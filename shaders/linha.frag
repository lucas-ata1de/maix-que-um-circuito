#version 400 core
uniform vec3 u_cor;
out vec4 outfragcolor;

void main() {
    outfragcolor = vec4(u_cor, 1.0);
}
