#version 400 core
layout(location = 0) in vec3 vPosition;

uniform mat4 u_modelo, u_visao, u_projecao;
uniform float u_tempo;
uniform float u_amp;
uniform float u_vel;
uniform float u_seed;

void main() {
    vec3 pos = vPosition;
    float envelope = sin(3.14159265 * pos.z);
    pos.x += u_amp * envelope * sin(pos.z * 26.0 + u_tempo * u_vel + u_seed);
    pos.y += u_amp * envelope * cos(pos.z * 21.0 - u_tempo * u_vel * 0.8 + u_seed);
    gl_Position = u_projecao * u_visao * u_modelo * vec4(pos, 1.0);
}
