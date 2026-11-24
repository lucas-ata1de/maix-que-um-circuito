#version 400 core

layout(location = 0) in vec4 vPosition;
layout(location = 1) in vec4 vNorm;

uniform mat4 u_modelo, u_visao, u_projecao;
out vec3 fN;

void main() {
    gl_Position = u_projecao * u_visao * u_modelo * vPosition;
    fN = vec4(u_modelo * vNorm).xyz;
}
