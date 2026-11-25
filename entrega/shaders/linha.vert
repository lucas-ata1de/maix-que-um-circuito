#version 400 core

in vec3 in_position;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform float u_tempo;
uniform float u_amp;
uniform float u_vel;
uniform float u_seed;

void main() {
    vec3 pos = in_position;
    if (u_amp > 0.0) {
        float envelope = sin(3.14159265 * pos.z);
        pos.x += u_amp * envelope * sin(pos.z * 26.0 + u_tempo * u_vel + u_seed);
        pos.y += u_amp * envelope * cos(pos.z * 21.0 - u_tempo * u_vel * 0.8 + u_seed);
    }
    gl_Position = u_projection * u_view * u_model * vec4(pos, 1.0);
}
