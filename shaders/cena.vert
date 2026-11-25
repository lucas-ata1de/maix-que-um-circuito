#version 400 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_uv;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat3 u_normal_matrix;

out vec3 v_pos_view;
out vec3 v_normal_view;
out vec2 v_uv;

void main() {
    vec4 pos_view = u_view * u_model * vec4(in_position, 1.0);
    v_pos_view = pos_view.xyz;
    v_normal_view = u_normal_matrix * in_normal;
    v_uv = in_uv;
    gl_Position = u_projection * pos_view;
}
