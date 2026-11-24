#version 400 core

in vec3 fN;
out vec4 outfragcolor;

void main() {
    vec3 N = normalize(fN);
    outfragcolor = vec4(N * 0.5 + 0.5, 1.0);
}
