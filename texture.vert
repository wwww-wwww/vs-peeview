#version 130

out highp vec2 texCoord;

uniform int in_color_space;
uniform int in_range;
uniform int in_bit_depth;

flat out int color_space;
flat out int range;
flat out int bit_depth;

void main(void)
{
    color_space = in_color_space;
    range = in_range;
    bit_depth = in_bit_depth;

    texCoord = gl_MultiTexCoord0.xy;
    gl_Position = gl_Vertex;
}
