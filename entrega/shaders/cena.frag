#version 400 core
// Blinn-Phong no Espaco da Camera com luz direcional, pontuais e choques localizados.

in vec3 v_pos_view;
in vec3 v_normal_view;
in vec2 v_uv;

out vec4 frag_color;

struct Material {
    vec3 ka;
    vec3 kd;
    vec3 ks;
    float shininess;
};

struct LuzDirecional {
    int ativa;
    vec3 direcao_view;
    vec3 cor;
    float fator_amb;
};

struct LuzPontual {
    int ativa;
    vec3 pos_view;
    vec3 cor;
    float fator_amb;
    float kc;
    float kl;
    float kq;
};

#define MAX_PONTUAIS 4
#define MAX_CHOQUES_TORRE 24
#define MAX_CHOQUES_ARESTA 48

uniform Material u_material;
uniform sampler2D u_textura;
uniform int u_codificar_srgb;

uniform LuzDirecional u_luz_dir;
uniform int u_num_pontuais;
uniform LuzPontual u_pontuais[MAX_PONTUAIS];

uniform int u_choques_torre_ativos;
uniform int u_num_choques_torre;
uniform vec4 u_choques_torre_params;
uniform float u_choques_torre_raio;
uniform vec3 u_choques_torre_pos[MAX_CHOQUES_TORRE];
uniform vec3 u_choques_torre_cor[MAX_CHOQUES_TORRE];

uniform int u_choques_aresta_ativos;
uniform int u_num_choques_aresta;
uniform vec4 u_choques_aresta_params;
uniform float u_choques_aresta_raio;
uniform vec3 u_cor_choque_corte;
uniform vec3 u_cor_choque_fora;
uniform vec4 u_choques_aresta_a[MAX_CHOQUES_ARESTA];
uniform vec4 u_choques_aresta_b[MAX_CHOQUES_ARESTA];

vec3 avaliar_blinn_phong(
    vec3 N, vec3 V, vec3 L,
    vec3 cor_luz, float fator_amb,
    vec3 ka_eff, vec3 kd_eff
) {
    float ndotl = max(dot(N, L), 0.0);
    float spec = 0.0;
    if (ndotl > 0.0) {
        vec3 H = normalize(L + V);
        spec = pow(max(dot(N, H), 0.0), u_material.shininess);
    }
    vec3 ambiente = fator_amb * ka_eff;
    vec3 difuso = ndotl * kd_eff;
    vec3 especular = spec * u_material.ks;
    return cor_luz * (ambiente + difuso + especular);
}

float atenuacao_local(float d, vec3 coefs, float raio) {
    if (d >= raio) {
        return 0.0;
    }
    float u = d / max(raio, 1e-4);
    float janela = 1.0 - u * u;
    float denom = coefs.x + coefs.y * d + coefs.z * d * d;
    return (janela * janela) / max(denom, 1e-6);
}

vec3 linear_para_srgb(vec3 c) {
    vec3 limpo = max(c, vec3(0.0));
    vec3 baixo = 12.92 * limpo;
    vec3 alto = 1.055 * pow(limpo, vec3(1.0 / 2.4)) - 0.055;
    return mix(baixo, alto, step(vec3(0.0031308), limpo));
}

void main() {
    vec3 N = normalize(v_normal_view);
    vec3 V = normalize(-v_pos_view);

    vec3 tex_cor = texture(u_textura, v_uv).rgb;
    vec3 ka_eff = u_material.ka * tex_cor;
    vec3 kd_eff = u_material.kd * tex_cor;

    vec3 cor_total = vec3(0.0);

    if (u_luz_dir.ativa != 0) {
        vec3 L_dir = normalize(-u_luz_dir.direcao_view);
        cor_total += avaliar_blinn_phong(
            N, V, L_dir,
            u_luz_dir.cor, u_luz_dir.fator_amb,
            ka_eff, kd_eff
        );
    }

    int n_pont = clamp(u_num_pontuais, 0, MAX_PONTUAIS);
    for (int i = 0; i < n_pont; ++i) {
        if (u_pontuais[i].ativa == 0) {
            continue;
        }
        vec3 delta = u_pontuais[i].pos_view - v_pos_view;
        float d = length(delta);
        vec3 L_pont = delta / max(d, 1e-6);
        float denom = u_pontuais[i].kc
            + u_pontuais[i].kl * d
            + u_pontuais[i].kq * d * d;
        float aten = 1.0 / max(denom, 1e-6);
        cor_total += aten * avaliar_blinn_phong(
            N, V, L_pont,
            u_pontuais[i].cor, u_pontuais[i].fator_amb,
            ka_eff, kd_eff
        );
    }

    if (u_choques_torre_ativos != 0) {
        int n_t = clamp(u_num_choques_torre, 0, MAX_CHOQUES_TORRE);
        for (int i = 0; i < n_t; ++i) {
            vec3 delta = u_choques_torre_pos[i] - v_pos_view;
            float d = length(delta);
            float aten = atenuacao_local(d, u_choques_torre_params.xyz, u_choques_torre_raio);
            if (aten <= 0.0) {
                continue;
            }
            vec3 L_t = delta / max(d, 1e-6);
            cor_total += aten * avaliar_blinn_phong(
                N, V, L_t,
                u_choques_torre_cor[i], u_choques_torre_params.w,
                ka_eff, kd_eff
            );
        }
    }

    if (u_choques_aresta_ativos != 0) {
        int n_a = clamp(u_num_choques_aresta, 0, MAX_CHOQUES_ARESTA);
        for (int i = 0; i < n_a; ++i) {
            vec3 A = u_choques_aresta_a[i].xyz;
            vec3 B = u_choques_aresta_b[i].xyz;
            vec3 ab = B - A;
            float t = clamp(
                dot(v_pos_view - A, ab) / max(dot(ab, ab), 1e-6),
                0.0,
                1.0
            );
            vec3 ponto_prox = A + t * ab;
            vec3 delta = ponto_prox - v_pos_view;
            float d = length(delta);
            float aten = atenuacao_local(d, u_choques_aresta_params.xyz, u_choques_aresta_raio);
            if (aten <= 0.0) {
                continue;
            }
            vec3 L_a = delta / max(d, 1e-6);
            vec3 cor_base = (u_choques_aresta_b[i].w > 0.5)
                ? u_cor_choque_corte
                : u_cor_choque_fora;
            float intens = u_choques_aresta_a[i].w;
            cor_total += aten * avaliar_blinn_phong(
                N, V, L_a,
                cor_base * intens, u_choques_aresta_params.w,
                ka_eff, kd_eff
            );
        }
    }

    vec3 rgb = (u_codificar_srgb != 0)
        ? linear_para_srgb(cor_total)
        : cor_total;
    frag_color = vec4(rgb, 1.0);
}
