#define NOMINMAX
#include <windows.h>
#include <cstdio>
#include <string>
#include <vector>
#include "dlss_bridge.h"
#include "nvsdk_ngx_helpers_vk.h"
#include "nvsdk_ngx_helpers.h"
#define API extern "C" __declspec(dllexport)
static VkDevice device;
static NVSDK_NGX_Parameter* params;
static NVSDK_NGX_Handle* feature;
static std::string error;
static std::string description;
static uint32_t rw,rh,ow,oh,mode,hdr;
static bool initialized;
static std::wstring selected_dll;
static int check(NVSDK_NGX_Result r,const char* operation) {
    if (NVSDK_NGX_SUCCEED(r)) return 1;
    char b[192]; std::snprintf(b,sizeof(b),"%s failed: NGX 0x%08x",operation,unsigned(r)); error=b; return 0;
}
API const char* bb_dlss_error() { return error.c_str(); }
API const char* bb_dlss_info() { return description.c_str(); }
API int bb_dlss_extensions(unsigned* ic,const char*** ie,unsigned* dc,const char*** de) {
    return check(NVSDK_NGX_VULKAN_RequiredExtensions(ic,ie,dc,de),"extension query");
}
API void bb_dlss_close() {
    std::puts("DLSS: releasing feature"); std::fflush(stdout);
    if (feature) NVSDK_NGX_VULKAN_ReleaseFeature(feature);
    std::puts("DLSS: destroying parameters"); std::fflush(stdout);
    if (params) NVSDK_NGX_VULKAN_DestroyParameters(params);
    std::puts("DLSS: shutting down NGX"); std::fflush(stdout);
    if (initialized) NVSDK_NGX_VULKAN_Shutdown1(device);
    std::puts("DLSS: shutdown complete"); std::fflush(stdout);
    feature=nullptr; params=nullptr; initialized=false;
}
API int bb_dlss_init(VkInstance instance,VkPhysicalDevice physical,VkDevice dev,
                    PFN_vkGetInstanceProcAddr gipa,PFN_vkGetDeviceProcAddr gdpa,const wchar_t* directory) {
    device=dev;
    std::wstring dll=std::wstring(directory)+L"\\nvngx_dlss.dll";
    selected_dll=dll;
    if (GetFileAttributesW(dll.c_str())==INVALID_FILE_ATTRIBUTES) { error="Selected directory has no nvngx_dlss.dll"; return 0; }
    const wchar_t* paths[]={directory};
    NVSDK_NGX_FeatureCommonInfo info{};
    info.PathListInfo={paths,1};
    // Unique project identity; no borrowed game application ID.
    if (!check(NVSDK_NGX_VULKAN_Init_with_ProjectID("87f2ee83-3d73-4d38-b565-52d253275662",
        NVSDK_NGX_ENGINE_TYPE_CUSTOM,"bbport-windows-1",L".",instance,physical,dev,gipa,gdpa,&info),"NGX init")) return 0;
    initialized=true;
    if (!check(NVSDK_NGX_VULKAN_GetCapabilityParameters(&params),"capabilities")) return 0;
    int available=0;
    if (!check(params->Get(NVSDK_NGX_Parameter_SuperSampling_Available,&available),"DLSS availability") || !available) {
        error="DLSS Super Resolution unavailable on this driver/device"; return 0;
    }
    return 1;
}
API int bb_dlss_eval(const BbDlssFrame* f) {
    if (!initialized || !params) { error="DLSS not initialized"; return 0; }
    if (feature && (rw!=f->width || rh!=f->height || ow!=f->output.width || oh!=f->output.height || mode!=f->preset || hdr!=f->hdr)) {
        error="DLSS input configuration changed: restart required"; return 0;
    }
    if (!feature) {
        NVSDK_NGX_DLSS_Create_Params c{};
        c.Feature.InWidth=f->width; c.Feature.InHeight=f->height;
        c.Feature.InTargetWidth=f->output.width; c.Feature.InTargetHeight=f->output.height;
        c.Feature.InPerfQualityValue = f->width==f->output.width && f->height==f->output.height ? NVSDK_NGX_PerfQuality_Value_DLAA :
            f->preset==4 ? NVSDK_NGX_PerfQuality_Value_UltraPerformance : f->preset==3 ? NVSDK_NGX_PerfQuality_Value_MaxPerf : f->preset==2 ? NVSDK_NGX_PerfQuality_Value_Balanced : NVSDK_NGX_PerfQuality_Value_MaxQuality;
        unsigned optimal_w=0,optimal_h=0,max_w=0,max_h=0,min_w=0,min_h=0; float sharpness=0;
        if (!check(NGX_DLSS_GET_OPTIMAL_SETTINGS(params,f->output.width,f->output.height,c.Feature.InPerfQualityValue,
            &optimal_w,&optimal_h,&max_w,&max_h,&min_w,&min_h,&sharpness),"DLSS supported sizes")) return 0;
        if (f->width<min_w || f->height<min_h || f->width>max_w || f->height>max_h) {
            char b[160]; std::snprintf(b,sizeof(b),"Requested %ux%u outside DLL supported range %ux%u..%ux%u",f->width,f->height,min_w,min_h,max_w,max_h);error=b;return 0;
        }
        c.InFeatureCreateFlags=NVSDK_NGX_DLSS_Feature_Flags_MVLowRes | NVSDK_NGX_DLSS_Feature_Flags_AutoExposure;
        if (f->hdr) c.InFeatureCreateFlags |= NVSDK_NGX_DLSS_Feature_Flags_IsHDR;
        if (!check(NGX_VULKAN_CREATE_DLSS_EXT1(device,f->cmd,1,1,&feature,params,&c),"create DLSS")) return 0;
        if (HMODULE loaded=GetModuleHandleW(L"nvngx_dlss.dll")) {
            wchar_t path[32768]; GetModuleFileNameW(loaded,path,32768);
            if (_wcsicmp(path,selected_dll.c_str())!=0) { error="NGX loaded a different DLSS DLL than requested"; return 0; }
            DWORD ignored=0,size=GetFileVersionInfoSizeW(path,&ignored);
            std::vector<char> bytes(size);
            VS_FIXEDFILEINFO* version=nullptr; UINT length=0;
            if (size && GetFileVersionInfoW(path,0,size,bytes.data()) && VerQueryValueW(bytes.data(),L"\\",(void**)&version,&length)) {
                std::printf("DLSS loaded version: %u.%u.%u.%u\n",HIWORD(version->dwFileVersionMS),LOWORD(version->dwFileVersionMS),HIWORD(version->dwFileVersionLS),LOWORD(version->dwFileVersionLS));
                char v[80];std::snprintf(v,sizeof(v),"%u.%u.%u.%u",HIWORD(version->dwFileVersionMS),LOWORD(version->dwFileVersionMS),HIWORD(version->dwFileVersionLS),LOWORD(version->dwFileVersionLS));
                int count=WideCharToMultiByte(CP_UTF8,0,path,-1,nullptr,0,nullptr,nullptr);
                std::string utf8(count,'\0');WideCharToMultiByte(CP_UTF8,0,path,-1,utf8.data(),count,nullptr,nullptr);utf8.pop_back();
                description=std::string(v)+" | "+utf8;
                std::fflush(stdout);
            }
        } else { error="Cannot verify loaded DLSS module"; return 0; }
        rw=f->width;rh=f->height;ow=f->output.width;oh=f->output.height;mode=f->preset;hdr=f->hdr;
    }
    auto resource=[](const BbDlssImage& i,bool depth,bool writable) {
        return NVSDK_NGX_Create_ImageView_Resource_VK(i.view,i.image,
            {VkImageAspectFlags(depth?VK_IMAGE_ASPECT_DEPTH_BIT:VK_IMAGE_ASPECT_COLOR_BIT),0,1,0,1},i.format,i.width,i.height,writable);
    };
    auto color=resource(f->color,false,false), depth=resource(f->depth,true,false),
         motion=resource(f->motion,false,false), output=resource(f->output,false,true);
    NVSDK_NGX_VK_DLSS_Eval_Params e{};
    e.Feature.pInColor=&color; e.Feature.pInOutput=&output;
    e.pInDepth=&depth; e.pInMotionVectors=&motion;
    e.InJitterOffsetX=f->jitter_x; e.InJitterOffsetY=f->jitter_y;
    e.InMVScaleX=1.0f; e.InMVScaleY=1.0f;
    e.InRenderSubrectDimensions={f->width,f->height}; e.InReset=f->reset;
    e.InPreExposure=1.0f; e.InExposureScale=1.0f;
    return check(NGX_VULKAN_EVALUATE_DLSS_EXT(f->cmd,feature,params,&e),"evaluate DLSS");
}
