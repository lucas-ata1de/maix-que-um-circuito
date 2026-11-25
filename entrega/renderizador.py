"""Fachada unica de renderizacao OpenGL 4.0 Core / ModernGL.

Encapsula compilacao de shaders, cache de VAOs, textura branca 1x1 (Null Object),
calculo da Matriz Normal na CPU, conversao das fontes de luz (direcional,
pontuais e choques eletricos de torres e arestas) para o Espaco da Camera,
gerenciamento de GL_FRAMEBUFFER_SRGB e as tres passadas de desenho.
"""

from pathlib import Path
from typing import Any, Optional

import glm
import moderngl
import numpy as np

import texturas as tex_mod
from material import CenaLuzes, Material

GL_FRAMEBUFFER_SRGB = 0x8DB9
MAX_PONTUAIS = 4
MAX_CHOQUES_TORRE = 24
MAX_CHOQUES_ARESTA = 48

CAMPOS_CENA: tuple[tuple[str, str], ...] = (
    ("3f", "in_position"),
    ("3f", "in_normal"),
    ("2f", "in_uv"),
)
CAMPOS_LINHA: tuple[tuple[str, str], ...] = (("3f", "in_position"),)


class Renderizador:
    """Unica classe do projeto que conhece shaders, VAOs e uniforms GLSL."""

    def __init__(
        self,
        ctx: moderngl.Context,
        pasta_shaders: str | Path = "shaders",
        usar_framebuffer_srgb: bool = True,
    ) -> None:
        """Compila os programas GLSL e inicializa caches internos da fachada."""
        self.ctx = ctx
        self.usar_framebuffer_srgb = usar_framebuffer_srgb

        pasta = Path(pasta_shaders)
        self.prog_cena = ctx.program(
            vertex_shader=(pasta / "cena.vert").read_text(encoding="utf-8"),
            fragment_shader=(pasta / "cena.frag").read_text(encoding="utf-8"),
        )
        self.prog_linha = ctx.program(
            vertex_shader=(pasta / "linha.vert").read_text(encoding="utf-8"),
            fragment_shader=(pasta / "linha.frag").read_text(encoding="utf-8"),
        )

        self._tex_branca = ctx.texture((1, 1), 4, b"\xff\xff\xff\xff")
        self._tex_branca.filter = (moderngl.NEAREST, moderngl.NEAREST)

        self._texturas: dict[str, moderngl.Texture] = {}
        self._vaos: dict[tuple[int, int, int], moderngl.VertexArray] = {}
        self._matriz_visao = glm.mat4(1.0)

        self._buf_torre_pos = np.zeros((MAX_CHOQUES_TORRE, 3), dtype="f4")
        self._buf_torre_cor = np.zeros((MAX_CHOQUES_TORRE, 3), dtype="f4")
        self._buf_aresta_a = np.zeros((MAX_CHOQUES_ARESTA, 4), dtype="f4")
        self._buf_aresta_b = np.zeros((MAX_CHOQUES_ARESTA, 4), dtype="f4")

    @staticmethod
    def _enviar(prog: moderngl.Program, nome: str, valor: Any) -> None:
        """Envia um uniform ao programa GLSL somente se estiver ativo no shader."""
        if nome not in prog:
            return
        if isinstance(valor, (glm.mat3, glm.mat4)):
            prog[nome].write(valor.to_bytes())
        elif isinstance(valor, (glm.vec2, glm.vec3, glm.vec4)):
            prog[nome].value = tuple(valor)
        elif isinstance(valor, np.ndarray):
            prog[nome].write(np.ascontiguousarray(valor, dtype="f4").tobytes())
        else:
            prog[nome].value = valor

    @staticmethod
    def _matriz_normal(mv: glm.mat4) -> glm.mat3:
        """Calcula a inversa transposta da parte linear 3x3 de V * M."""
        return glm.transpose(glm.inverse(glm.mat3(mv)))

    def _vao_de(
        self,
        prog: moderngl.Program,
        vbo: moderngl.Buffer,
        ibo: Optional[moderngl.Buffer],
        campos: tuple[tuple[str, str], ...],
    ) -> moderngl.VertexArray:
        """Recupera ou cria em cache o VAO para a combinacao (programa, VBO, IBO)."""
        chave = (id(prog), id(vbo), id(ibo) if ibo is not None else 0)
        vao = self._vaos.get(chave)
        if vao is not None:
            return vao

        formato: list[str] = []
        nomes: list[str] = []
        for tamanho, nome in campos:
            if nome in prog:
                formato.append(tamanho)
                nomes.append(nome)
            else:
                formato.append(f"{tamanho[0]}x4")

        vao = self.ctx.vertex_array(
            prog,
            [(vbo, " ".join(formato), *nomes)],
            index_buffer=ibo,
        )
        self._vaos[chave] = vao
        return vao

    @property
    def _flag_codificar_srgb(self) -> int:
        """Retorna 0 quando GL_FRAMEBUFFER_SRGB esta ativo, ou 1 para codificar no shader."""
        return 0 if self.usar_framebuffer_srgb else 1

    def carregar_textura(
        self,
        nome: str,
        caminho: str | Path,
        *,
        srgb: bool = True,
        repetir: bool = True,
        mipmap: bool = True,
    ) -> moderngl.Texture:
        """Carrega imagem via texturas.py (GL_SRGB8_ALPHA8, mipmaps e anisotropia)."""
        imagem = tex_mod.ler(caminho)
        tex = tex_mod.carregar(self.ctx, imagem, srgb=srgb, mipmap=mipmap)
        tex.repeat_x = repetir
        tex.repeat_y = repetir
        self._texturas[nome] = tex
        return tex

    def limpar_tela(self, cor_fundo: tuple[float, float, float, float]) -> None:
        """Limpa o framebuffer sem dupla codificacao sRGB na cor de fundo."""
        self.ctx.disable_direct(GL_FRAMEBUFFER_SRGB)
        self.ctx.clear(*cor_fundo, depth=1.0)
        if self.usar_framebuffer_srgb:
            self.ctx.enable_direct(GL_FRAMEBUFFER_SRGB)

    def iniciar_cena_3d(
        self,
        visao: glm.mat4,
        projecao: glm.mat4,
        luzes: CenaLuzes,
    ) -> None:
        """Configura camera e todas as fontes de luz no Espaco da Camera (1x/quadro)."""
        self._matriz_visao = visao
        prog = self.prog_cena

        self._enviar(prog, "u_view", visao)
        self._enviar(prog, "u_projection", projecao)
        self._enviar(prog, "u_textura", 0)
        self._enviar(prog, "u_codificar_srgb", self._flag_codificar_srgb)

        ld = luzes.direcional
        dir_view = glm.normalize(glm.mat3(visao) * ld.direcao)
        self._enviar(prog, "u_luz_dir.ativa", int(ld.ativa))
        self._enviar(prog, "u_luz_dir.direcao_view", dir_view)
        self._enviar(prog, "u_luz_dir.cor", ld.cor)
        self._enviar(prog, "u_luz_dir.fator_amb", float(ld.fator_amb))

        pontuais = luzes.pontuais[:MAX_PONTUAIS]
        self._enviar(prog, "u_num_pontuais", len(pontuais))
        for i, lp in enumerate(pontuais):
            pos_view = glm.vec3(visao * glm.vec4(lp.posicao, 1.0))
            pref = f"u_pontuais[{i}]"
            self._enviar(prog, f"{pref}.ativa", int(lp.ativa))
            self._enviar(prog, f"{pref}.pos_view", pos_view)
            self._enviar(prog, f"{pref}.cor", lp.cor)
            self._enviar(prog, f"{pref}.fator_amb", float(lp.fator_amb))
            self._enviar(prog, f"{pref}.kc", float(lp.kc))
            self._enviar(prog, f"{pref}.kl", float(lp.kl))
            self._enviar(prog, f"{pref}.kq", float(lp.kq))

        ch = luzes.choques
        torres_ativas = ch.torres_ativas and len(ch.torres) > 0
        self._enviar(prog, "u_choques_torre_ativos", int(torres_ativas))
        if torres_ativas:
            n_t = min(len(ch.torres), MAX_CHOQUES_TORRE)
            self._enviar(prog, "u_num_choques_torre", n_t)
            self._enviar(
                prog,
                "u_choques_torre_params",
                (ch.torre_kc, ch.torre_kl, ch.torre_kq, ch.torre_fator_amb),
            )
            self._enviar(prog, "u_choques_torre_raio", float(ch.torre_raio))
            for i in range(n_t):
                lt = ch.torres[i]
                pv = visao * glm.vec4(lt.posicao, 1.0)
                self._buf_torre_pos[i] = (pv.x, pv.y, pv.z)
                self._buf_torre_cor[i] = (lt.cor.x, lt.cor.y, lt.cor.z)
            self._enviar(prog, "u_choques_torre_pos", self._buf_torre_pos)
            self._enviar(prog, "u_choques_torre_cor", self._buf_torre_cor)
        else:
            self._enviar(prog, "u_num_choques_torre", 0)

        arestas_ativas = ch.arestas_ativas and len(ch.arestas) > 0
        self._enviar(prog, "u_choques_aresta_ativos", int(arestas_ativas))
        if arestas_ativas:
            if len(ch.arestas) > MAX_CHOQUES_ARESTA:
                arestas_ord = sorted(ch.arestas, key=lambda a: not a.no_corte)
            else:
                arestas_ord = ch.arestas
            n_a = min(len(arestas_ord), MAX_CHOQUES_ARESTA)
            self._enviar(prog, "u_num_choques_aresta", n_a)
            self._enviar(
                prog,
                "u_choques_aresta_params",
                (ch.aresta_kc, ch.aresta_kl, ch.aresta_kq, ch.aresta_fator_amb),
            )
            self._enviar(prog, "u_choques_aresta_raio", float(ch.aresta_raio))
            self._enviar(prog, "u_cor_choque_corte", ch.cor_aresta_corte)
            self._enviar(prog, "u_cor_choque_fora", ch.cor_aresta_fora)
            for i in range(n_a):
                la = arestas_ord[i]
                pa = visao * glm.vec4(la.ponto_a, 1.0)
                pb = visao * glm.vec4(la.ponto_b, 1.0)
                self._buf_aresta_a[i] = (pa.x, pa.y, pa.z, float(la.intensidade))
                self._buf_aresta_b[i] = (pb.x, pb.y, pb.z, 1.0 if la.no_corte else 0.0)
            self._enviar(prog, "u_choques_aresta_a", self._buf_aresta_a)
            self._enviar(prog, "u_choques_aresta_b", self._buf_aresta_b)
        else:
            self._enviar(prog, "u_num_choques_aresta", 0)

    def desenhar_objeto(
        self,
        vbo: moderngl.Buffer,
        material: Material,
        modelo: glm.mat4,
        ibo: Optional[moderngl.Buffer] = None,
        modo: int = moderngl.TRIANGLES,
    ) -> None:
        """Desenha uma instancia 3D iluminada com Matriz Normal e textura."""
        prog = self.prog_cena
        tex = (
            self._texturas.get(material.textura, self._tex_branca)
            if material.textura is not None
            else self._tex_branca
        )
        tex.use(location=0)

        mv = self._matriz_visao * modelo
        self._enviar(prog, "u_model", modelo)
        self._enviar(prog, "u_normal_matrix", self._matriz_normal(mv))
        self._enviar(prog, "u_uv_escala", material.uv_escala)
        self._enviar(prog, "u_material.ka", material.ka)
        self._enviar(prog, "u_material.kd", material.kd)
        self._enviar(prog, "u_material.ks", material.ks)
        self._enviar(prog, "u_material.shininess", float(material.shininess))

        vao = self._vao_de(prog, vbo, ibo, CAMPOS_CENA)
        vao.render(mode=modo)

    def iniciar_linhas_3d(
        self,
        visao: glm.mat4,
        projecao: glm.mat4,
        tempo: float = 0.0,
    ) -> None:
        """Configura o shader leve de linhas 3D (1x por quadro)."""
        prog = self.prog_linha
        self._enviar(prog, "u_view", visao)
        self._enviar(prog, "u_projection", projecao)
        self._enviar(prog, "u_tempo", float(tempo))
        self._enviar(prog, "u_codificar_srgb", self._flag_codificar_srgb)

    def desenhar_linha(
        self,
        vbo: moderngl.Buffer,
        modelo: glm.mat4,
        cor: glm.vec3 | glm.vec4 | tuple[float, float, float] | tuple[float, float, float, float],
        modo: int = moderngl.LINE_STRIP,
        *,
        ibo: Optional[moderngl.Buffer] = None,
        amp: float = 0.0,
        vel: float = 0.0,
        seed: float = 0.0,
    ) -> None:
        """Desenha primitivas de linha (LINE_STRIP, LINE_LOOP, LINES) em luz linear."""
        prog = self.prog_linha
        if isinstance(cor, glm.vec4):
            cor_rgba = cor
        elif isinstance(cor, glm.vec3):
            cor_rgba = glm.vec4(cor.x, cor.y, cor.z, 1.0)
        elif len(cor) == 4:
            cor_rgba = glm.vec4(cor[0], cor[1], cor[2], cor[3])
        else:
            cor_rgba = glm.vec4(cor[0], cor[1], cor[2], 1.0)

        self._enviar(prog, "u_model", modelo)
        self._enviar(prog, "u_cor", cor_rgba)
        self._enviar(prog, "u_amp", float(amp))
        self._enviar(prog, "u_vel", float(vel))
        self._enviar(prog, "u_seed", float(seed))

        vao = self._vao_de(prog, vbo, ibo, CAMPOS_LINHA)
        vao.render(mode=modo)

    def iniciar_placar_2d(self, largura: int, altura: int) -> None:
        """Prepara projecao ortografica 2D com teste de profundidade desligado."""
        self.ctx.disable(moderngl.DEPTH_TEST)
        prog = self.prog_linha
        proj_ortho = glm.ortho(
            0.0,
            float(max(1, largura)),
            0.0,
            float(max(1, altura)),
            -1.0,
            1.0,
        )
        self._enviar(prog, "u_view", glm.mat4(1.0))
        self._enviar(prog, "u_projection", proj_ortho)
        self._enviar(prog, "u_tempo", 0.0)
        self._enviar(prog, "u_codificar_srgb", self._flag_codificar_srgb)

    def desenhar_placar_2d(
        self,
        vbo: moderngl.Buffer,
        modelo: glm.mat4,
        cor: glm.vec3 | glm.vec4 | tuple[float, float, float] | tuple[float, float, float, float],
        modo: int = moderngl.LINES,
        ibo: Optional[moderngl.Buffer] = None,
    ) -> None:
        """Desenha geometria 2D do placar sem deformacao de onda."""
        self.desenhar_linha(vbo, modelo, cor, modo=modo, ibo=ibo, amp=0.0, vel=0.0, seed=0.0)

    def finalizar_placar_2d(self) -> None:
        """Reativa o teste de profundidade apos o placar 2D."""
        self.ctx.enable(moderngl.DEPTH_TEST)

    def liberar(self) -> None:
        """Libera VAOs, texturas e programas alocados na GPU."""
        for vao in self._vaos.values():
            vao.release()
        self._vaos.clear()
        for tex in self._texturas.values():
            tex.release()
        self._texturas.clear()
        self._tex_branca.release()
        self.prog_cena.release()
        self.prog_linha.release()
