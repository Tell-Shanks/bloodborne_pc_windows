#pragma once
#include <vulkan/vulkan.h>
#include <stdint.h>
// C ABI: the renderer uses MinGW, NGX is linked by the MSVC bridge.
struct BbDlssImage { VkImage image; VkImageView view; VkFormat format; uint32_t width,height; };
struct BbDlssFrame {
    VkCommandBuffer cmd;
    BbDlssImage color,depth,motion,output;
    uint32_t width,height,preset,reset,hdr;
    float jitter_x,jitter_y,frame_ms;
};
typedef int (*BbDlssInit)(VkInstance,VkPhysicalDevice,VkDevice,PFN_vkGetInstanceProcAddr,PFN_vkGetDeviceProcAddr,const wchar_t*);
typedef int (*BbDlssEval)(const BbDlssFrame*);
typedef void (*BbDlssClose)();
typedef const char* (*BbDlssError)();
typedef int (*BbDlssExtensions)(unsigned*,const char***,unsigned*,const char***);
