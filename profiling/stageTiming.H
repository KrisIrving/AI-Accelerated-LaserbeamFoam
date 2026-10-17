// Coarse, exclusive observation only. No field, dictionary or solver changes.
#ifndef laserbeamFoam_stageTiming_H
#define laserbeamFoam_stageTiming_H
#include <chrono>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>

class StageTiming
{
public:
    enum Phase { INIT, OTHER, VOF, PROPS, LASER, MIXTURE, U, MTHD, T, P, TURB, OUTPUT, COUNT };
private:
    using Clock = std::chrono::steady_clock;
    bool enabled_;
    Phase active_ = INIT;
    Clock::time_point started_, previous_;
    std::int64_t nanos_[COUNT] = {};
    std::uint64_t calls_[COUNT] = {};
public:
    StageTiming()
    : enabled_(std::getenv("LBF_STAGE_TIMING") &&
        std::string(std::getenv("LBF_STAGE_TIMING")) == "1")
    {
        if (enabled_)
        {
            started_ = previous_ = Clock::now();
            calls_[INIT] = 1;
        }
    }
    void enter(Phase phase)
    {
        if (!enabled_) return;
        const auto now = Clock::now();
        nanos_[active_] += std::chrono::duration_cast<std::chrono::nanoseconds>
            (now - previous_).count();
        previous_ = now;
        active_ = phase;
        ++calls_[phase];
    }
    void finish()
    {
        if (!enabled_) return;
        const auto now = Clock::now();
        nanos_[active_] += std::chrono::duration_cast<std::chrono::nanoseconds>
            (now - previous_).count();
        const auto total = std::chrono::duration_cast<std::chrono::nanoseconds>
            (now - started_).count();
        const char* path = std::getenv("LBF_STAGE_TIMING_FILE");
        if (!path) throw std::runtime_error("Missing LBF_STAGE_TIMING_FILE");
        std::ofstream out(path);
        out << "phase,calls,wall_nanoseconds\n";
        const char* names[] = {"initialization", "other", "VOF", "updateProps",
            "laser_deposition", "mixture_correct", "U_equation", "MTHD_solve",
            "T_equation", "p_equation", "turbulence_correct", "native_output"};
        for (int i = 0; i < COUNT; ++i)
            out << names[i] << ',' << calls_[i] << ',' << nanos_[i] << '\n';
        out << "TOTAL,1," << total << '\n';
        out.close();
        if (!out) throw std::runtime_error("Cannot write stage timing");
        enabled_ = false;
    }
};
#endif
