#version 420

uniform sampler2D sColor0;
uniform sampler2D sColor1;
uniform sampler2D sColor2;
uniform sampler3D sLut;

in highp vec2 texCoord;
flat in int color_space;
flat in int range;
flat in int bit_depth;

out vec4 color;

// https://searchfox.org/mozilla-central/source/gfx/wr/webrender/res/yuv.glsl
const mat3 RgbFromYuv_Rec601 = mat3(
    1.00000, 1.00000, 1.00000,
    0.00000,-0.17207, 0.88600,
    0.70100,-0.35707, 0.00000
);

const mat3 RgbFromYuv_Rec709 = mat3(
    1.00000, 1.00000, 1.00000,
    0.00000,-0.09366, 0.92780,
    0.78740,-0.23406, 0.00000
);

const mat3 RgbFromYuv_Rec2020 = mat3(
    1.00000, 1.00000, 1.00000,
    0.00000,-0.08228, 0.94070,
    0.73730,-0.28568, 0.00000
);

const mat3 RgbFromYuv_GbrIdentity = mat3(
    0.0, 1.0, 0.0,
    0.0, 0.0, 1.0,
    1.0, 0.0, 0.0
);

/*
const mat3 Identity = mat3(
    1.0, 0.0, 0.0,
    0.0, 1.0, 0.0,
    0.0, 0.0, 1.0
);

const mat3 RgbFromGray = mat3(
    1.0, 0.0, 0.0,
    1.0, 0.0, 0.0,
    1.0, 0.0, 0.0
);
*/

#define YUV_COLOR_SPACE_REC709   0
#define YUV_COLOR_SPACE_REC601   1
#define YUV_COLOR_SPACE_REC2020  2
//#define YUV_COLOR_SPACE_IDENTITY 3
//#define YUV_COLOR_SPACE_GRAY     4

#define RANGE_NARROW 0
#define RANGE_FULL   1


vec4 yuv_channel_zero_one_identity(int bit_depth, float channel_max) {
    float all_ones_normalized = float((1 << bit_depth) - 1) / channel_max;
    return vec4(0.0, 0.0, all_ones_normalized, all_ones_normalized);
}

vec4 yuv_channel_zero_one_narrow_range(int bit_depth, float channel_max) {
    // Note: 512/1023 != 128/255
    ivec4 zero_one_ints = ivec4(16, 128, 235, 240) << (bit_depth - 8);
    return vec4(zero_one_ints) / channel_max;
}

vec4 yuv_channel_zero_one_full_range(int bit_depth, float channel_max) {
    vec4 narrow = yuv_channel_zero_one_narrow_range(bit_depth, channel_max);
    vec4 identity = yuv_channel_zero_one_identity(bit_depth, channel_max);
    return vec4(0.0, narrow.y, identity.z, identity.w);
}

struct YuvColorSamplingInfo {
    mat3 rgb_from_yuv;
    vec4 packed_zero_one_vals;
};

YuvColorSamplingInfo get_yuv_color_info(int color_space, int range, int bit_depth) {
    float channel_max = 255.0;
    if (bit_depth > 8) {
        channel_max = 65535.0;
    }

    if (color_space == YUV_COLOR_SPACE_REC709 && range == RANGE_NARROW) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec709,
                        yuv_channel_zero_one_narrow_range(bit_depth, channel_max));
    } else if (color_space == YUV_COLOR_SPACE_REC709 && range == RANGE_FULL) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec709,
                        yuv_channel_zero_one_full_range(bit_depth, channel_max));
    } else if (color_space == YUV_COLOR_SPACE_REC601 && range == RANGE_NARROW) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec601,
                        yuv_channel_zero_one_narrow_range(bit_depth, channel_max));
    } else if (color_space == YUV_COLOR_SPACE_REC601 && range == RANGE_FULL) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec601,
                        yuv_channel_zero_one_full_range(bit_depth, channel_max));
    } else if (color_space == YUV_COLOR_SPACE_REC2020 && range == RANGE_NARROW) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec2020,
                        yuv_channel_zero_one_narrow_range(bit_depth, channel_max));
    } else if (color_space == YUV_COLOR_SPACE_REC2020 && range == RANGE_FULL) {
        return YuvColorSamplingInfo(RgbFromYuv_Rec2020,
                        yuv_channel_zero_one_full_range(bit_depth, channel_max));
    } else {
        return YuvColorSamplingInfo(RgbFromYuv_GbrIdentity,
                        yuv_channel_zero_one_identity(bit_depth, channel_max));
    }
}

mediump vec3 sample_yuv(vec2 pos) {
    mediump vec3 ycbcr_sample = vec3(texture(sColor0, pos).r,
                                     texture(sColor1, pos).r,
                                     texture(sColor2, pos).r);
    YuvColorSamplingInfo color_info = get_yuv_color_info(color_space, range, bit_depth);
    vec2 zero = color_info.packed_zero_one_vals.xy;
    vec2 one = color_info.packed_zero_one_vals.zw;
    // Such that yuv_value = (ycbcr_sample - zero) / (one - zero)
    vec2 scale = 1.0 / (one - zero);
    mediump vec3 ycbcr_bias = zero.xyy;

    mat3 debiased_ycbcr = mat3(scale.x,     0.0,     0.0,
                                   0.0, scale.y,     0.0,
                                   0.0,     0.0, scale.y);

    mat3 rgb_from_yuv = color_info.rgb_from_yuv * debiased_ycbcr;
    mediump vec3 rgb = rgb_from_yuv * (ycbcr_sample - ycbcr_bias);
    rgb = clamp(rgb, 0.0, 1.0);
    return rgb;
}

void main(void) {
    mediump vec3 rgb = sample_yuv(texCoord);

    vec3 lut_size = vec3(textureSize(sLut, 0));
    vec3 table_pos = mix(0.5 / lut_size, 1.0 - 0.5 / lut_size, rgb.bgr);
    vec4 lut_rgba = texture(sLut, table_pos);

    color = vec4(lut_rgba.rgb, 1.0);
}
