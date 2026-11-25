#version 400 core
// Cor solida em espaco linear com codificacao sRGB opcional para linhas e placar.

uniform vec4 u_cor;
uniform int u_codificar_srgb;

out vec4 frag_color;

vec3 linear_para_srgb(vec3 c) {
    vec3 limpo = max(c, vec3(0.0));
    vec3 baixo = 12.92 * limpo;
    vec3 alto = 1.055 * pow(limpo, vec3(1.0 / 2.4)) - 0.055;
    return mix(baixo, alto, step(vec3(0.0031308), limpo));
}

void main() {
    vec3 rgb = (u_codificar_srgb != 0)
        ? linear_para_srgb(u_cor.rgb)
        : u_cor.rgb;
    frag_color = vec4(rgb, u_cor.a);
}
