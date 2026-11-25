#version 400 core

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
    vec3 direcao_view;   // direcao de propagacao dos raios no Espaco da Camera
    vec3 cor;            // intensidade RGB em espaco linear
    float fator_amb;     // fracao ambiente (ex.: 0.22)
};

struct LuzPontual {
    int ativa;
    vec3 pos_view;       // posicao no Espaco da Camera
    vec3 cor;            // intensidade RGB em espaco linear
    float fator_amb;     // fracao ambiente (ex.: 0.08)
    float kc;            // atenuacao constante
    float kl;            // atenuacao linear
    float kq;            // atenuacao quadratica
};

#define MAX_PONTUAIS 4

uniform Material u_material;
uniform sampler2D u_textura;
uniform int u_codificar_srgb;  // 0 = usa GL_FRAMEBUFFER_SRGB; 1 = codifica no shader

uniform LuzDirecional u_luz_dir;
uniform int u_num_pontuais;
uniform LuzPontual u_pontuais[MAX_PONTUAIS];

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

    vec3 rgb = (u_codificar_srgb != 0)
        ? linear_para_srgb(cor_total)
        : cor_total;
    frag_color = vec4(rgb, 1.0);
}
