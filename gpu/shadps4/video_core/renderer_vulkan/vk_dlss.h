#pragma once
#include <cstdio>
#include <filesystem>
#include <string>
#include "dlss_bridge.h"
#ifdef _WIN32
#include <windows.h>
#endif
namespace Vulkan {
class DlssUpscaler {
public:
    ~DlssUpscaler() {
#ifdef _WIN32
        if (close) close();
        if (module) FreeLibrary(module);
#endif
    }
    bool Record(VkInstance instance,VkPhysicalDevice physical,VkDevice device,
                PFN_vkGetInstanceProcAddr gipa,PFN_vkGetDeviceProcAddr gdpa,const BbDlssFrame& frame) {
#ifdef _WIN32
        if (failed) return false;
        if (!module) {
            wchar_t executable[32768];
            if (!GetModuleFileNameW(nullptr,executable,32768)) return Fail("Cannot locate renderer executable");
            auto bridge=std::filesystem::path(executable).parent_path()/L"bb-dlss-bridge.dll";
            module=LoadLibraryExW(bridge.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
            if (!module) return Fail("Cannot load bb-dlss-bridge.dll beside renderer");
            auto init=reinterpret_cast<BbDlssInit>(GetProcAddress(module,"bb_dlss_init"));
            eval=reinterpret_cast<BbDlssEval>(GetProcAddress(module,"bb_dlss_eval"));
            close=reinterpret_cast<BbDlssClose>(GetProcAddress(module,"bb_dlss_close"));
            error=reinterpret_cast<BbDlssError>(GetProcAddress(module,"bb_dlss_error"));
            info=reinterpret_cast<BbDlssError>(GetProcAddress(module,"bb_dlss_info"));
            if (!init || !eval || !close || !error) return Fail("DLSS bridge ABI mismatch");
            const char* configured=std::getenv("BB_DLSS_DIR");
            auto directory=std::filesystem::absolute(std::filesystem::u8path(configured && configured[0]?configured:"dlss"));
            std::printf("DLSS: selected library %s/nvngx_dlss.dll\n",directory.string().c_str());
            if (!init(instance,physical,device,gipa,gdpa,directory.c_str())) return Fail(error());
        }
        if (!eval(&frame)) return Fail(error());
        if (info && !reported) description=info();
        if (!reported) {
            const char* mode=frame.width==frame.output.width?"DLAA":"Super Resolution";
            std::string version=description.substr(0,description.find(" | "));
            std::string prefix=version.empty()?"DLSS":"DLSS "+version;
            char text[160];
            std::snprintf(text,sizeof(text),"%s  %ux%u -> %ux%u",prefix.c_str(),
                frame.width,frame.height,frame.output.width,frame.output.height);
            frame_info=text;
            std::printf("DLSS: active input %ux%u -> %ux%u (%s)\n",frame.width,frame.height,
                frame.output.width,frame.output.height,mode);
            reported=true;
        }
        return true;
#else
        return Fail("DLSS bridge is available on Windows only");
#endif
    }
    const char* Problem() const { return problem.c_str(); }
    const char* Description() const { return description.c_str(); }
    /// "version | input -> output (mode)", set once the first frame is evaluated.
    const char* FrameInfo() const { return frame_info.c_str(); }
private:
    bool Fail(const char* text) { problem=text; failed=true; std::printf("DLSS: %s\n",text); return false; }
    bool failed=false,reported=false;
    std::string problem,description,frame_info;
#ifdef _WIN32
    HMODULE module=nullptr;
    BbDlssEval eval=nullptr;
    BbDlssClose close=nullptr;
    BbDlssError error=nullptr;
    BbDlssError info=nullptr;
#endif
};
}
