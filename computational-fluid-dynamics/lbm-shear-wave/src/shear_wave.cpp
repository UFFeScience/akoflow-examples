#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <complex>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

constexpr std::array transverse_sizes{64, 80, 96, 112, 128, 160, 192, 256};
constexpr std::array relaxation_times{0.60, 0.65, 0.72, 0.80, 0.90, 1.00, 1.20, 1.50};
constexpr std::array mode_numbers{1, 2, 3, 4};
constexpr std::array amplitudes{0.0025, 0.005, 0.010, 0.020};
constexpr int case_count = transverse_sizes.size() * relaxation_times.size()
                         * mode_numbers.size() * amplitudes.size();
constexpr int streamwise_size = 8;
constexpr int fit_start = 32;
constexpr std::array cx{0, 1, 0, -1, 0, 1, -1, -1, 1};
constexpr std::array cy{0, 0, 1, 0, -1, 1, 1, -1, -1};
constexpr std::array weights{4.0/9, 1.0/9, 1.0/9, 1.0/9, 1.0/9,
                             1.0/36, 1.0/36, 1.0/36, 1.0/36};
using Population = std::array<double, 9>;

struct Scenario {
    int size;
    double tau;
    int mode;
    double amplitude;
};

struct Moments {
    double density = 0;
    double momentum_x = 0;
    double momentum_y = 0;
};

Scenario scenario(int id) {
    if (id == case_count) {
        return {64, 0.80, 1, 0};
    }
    const auto amplitude = amplitudes[id % amplitudes.size()];
    id /= amplitudes.size();
    const auto mode = mode_numbers[id % mode_numbers.size()];
    id /= mode_numbers.size();
    const auto tau = relaxation_times[id % relaxation_times.size()];
    const auto size = transverse_sizes[id / relaxation_times.size()];
    return {size, tau, mode, amplitude};
}

Moments moments(const Population& population) {
    Moments result;
    for (int i = 0; i < 9; ++i) {
        result.density += population[i];
        result.momentum_x += population[i] * cx[i];
        result.momentum_y += population[i] * cy[i];
    }
    return result;
}

double equilibrium(int direction, double density, double ux, double uy) {
    const double dot = cx[direction] * ux + cy[direction] * uy;
    return weights[direction] * density
         * (1 + 3 * dot + 4.5 * dot * dot - 1.5 * (ux * ux + uy * uy));
}

double linear_decay(double theta, double tau) {
    using Complex = std::complex<double>;
    constexpr std::array group_weights{1.0/6, 2.0/3, 1.0/6};
    std::array<Complex, 3> state{group_weights[0], group_weights[1], group_weights[2]};
    std::array<Complex, 3> phases;
    for (int i = 0; i < 3; ++i) {
        phases[i] = std::polar(1.0, -theta * (i - 1));
    }
    Complex scale{1.0};
    for (int step = 0; step < 160; ++step) {
        const Complex total = state[0] + state[1] + state[2];
        for (int i = 0; i < 3; ++i) {
            state[i] = phases[i] * ((1 - 1/tau) * state[i] + group_weights[i] * total/tau);
        }
        scale = state[0] + state[1] + state[2];
        for (auto& value : state) {
            value /= scale;
        }
    }
    return -std::log(std::abs(scale));
}

void advance(const std::vector<Population>& current,
             std::vector<Population>& next, int width, double tau) {
    #pragma omp parallel for schedule(static)
    for (int index = 0; index < static_cast<int>(current.size()); ++index) {
        const int x = index % streamwise_size;
        const int y = index / streamwise_size;
        const auto fluid = moments(current[index]);
        const double ux = fluid.momentum_x / fluid.density;
        const double uy = fluid.momentum_y / fluid.density;
        for (int i = 0; i < 9; ++i) {
            const int target_x = (x + cx[i] + streamwise_size) % streamwise_size;
            const int target_y = (y + cy[i] + width) % width;
            const int target = target_y * streamwise_size + target_x;
            next[target][i] = current[index][i]
                            - (current[index][i] - equilibrium(i, fluid.density, ux, uy)) / tau;
        }
    }
}

void simulate(int id, const std::filesystem::path& output) {
    const Scenario input = scenario(id);
    const bool rest = input.amplitude == 0;
    const double theta = 2 * std::numbers::pi * input.mode / input.size;
    const double continuum = (input.tau - 0.5) * theta * theta / 3;
    const int last = rest ? 64 : std::min(512, static_cast<int>(4 / continuum));
    const int cell_count = input.size * streamwise_size;
    std::vector<Population> current(cell_count), next(cell_count);
    std::vector<double> wave(input.size);
    for (int y = 0; y < input.size; ++y) {
        wave[y] = std::sin(theta * y);
        for (int x = 0; x < streamwise_size; ++x) {
            auto& population = current[y*streamwise_size+x];
            for (int i = 0; i < 9; ++i) {
                population[i] = equilibrium(i, 1, input.amplitude * wave[y], 0);
            }
        }
    }

    std::filesystem::create_directories(output);
    const auto label = "case-" + std::to_string(id);
    std::ofstream trace(output / (label + "-trace.csv"));
    trace.exceptions(std::ios::badbit | std::ios::failbit);
    trace << std::setprecision(17) << "step,mode_amplitude,mean_density,mean_momentum_x,mean_momentum_y\n";
    double initial_fit = 0, final_fit = 0, mass_error = 0, momentum_error = 0;
    for (int step = 0; step <= last; ++step) {
        double mode_amplitude = 0, density = 0, momentum_x = 0, momentum_y = 0;
        for (int index = 0; index < cell_count; ++index) {
            const auto fluid = moments(current[index]);
            density += fluid.density;
            momentum_x += fluid.momentum_x;
            momentum_y += fluid.momentum_y;
            mode_amplitude += fluid.momentum_x / fluid.density * wave[index / streamwise_size];
        }
        mode_amplitude *= 2.0 / cell_count;
        density /= cell_count;
        momentum_x /= cell_count;
        momentum_y /= cell_count;
        if (!std::isfinite(density) || !std::isfinite(mode_amplitude) ||
            !std::isfinite(momentum_x) || !std::isfinite(momentum_y)) {
            throw std::runtime_error("Non-finite fluid state");
        }
        trace << step << ',' << mode_amplitude << ',' << density << ',' << momentum_x
              << ',' << momentum_y << '\n';
        if (step == fit_start) initial_fit = mode_amplitude;
        if (step == last) final_fit = mode_amplitude;
        mass_error = std::max(mass_error, std::abs(density - 1));
        momentum_error = std::max({momentum_error, std::abs(momentum_x), std::abs(momentum_y)});
        if (step < last) {
            advance(current, next, input.size, input.tau);
            current.swap(next);
        }
    }
    const double discrete = rest ? 0 : linear_decay(theta, input.tau);
    const double measured = rest ? 0 : std::log(initial_fit / final_fit) / (last - fit_start);
    const double relative_error = rest ? 0 : std::abs(measured / discrete - 1);
    if (mass_error >= 1e-11 || momentum_error >= 1e-12 || !std::isfinite(measured)
        || relative_error >= 1e-6 || (!rest && std::abs(measured / continuum - 1) >= 0.05)
        || (rest && std::abs(final_fit) >= 1e-14)) {
        throw std::runtime_error("Shear rate or conservation check failed");
    }
    std::ofstream result(output / (label + "-metrics.csv"));
    result.exceptions(std::ios::badbit | std::ios::failbit);
    result << std::setprecision(17)
           << "id,size,tau,mode,initial_amplitude,steps,continuum_rate,discrete_rate,measured_rate,relative_error,mass_error,momentum_error\n"
           << id << ',' << input.size << ',' << input.tau << ',' << input.mode << ','
           << input.amplitude << ',' << last << ',' << (rest ? 0 : continuum) << ',' << discrete
           << ',' << measured << ',' << relative_error << ',' << mass_error << ',' << momentum_error << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: shear-wave CASE_ID OUTPUT_DIRECTORY\n";
        return 2;
    }
    std::string_view value(argv[1]);
    int id = -1;
    const auto parsed = std::from_chars(value.data(), value.data()+value.size(), id);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data()+value.size() ||
        id < 0 || id > case_count) {
        std::cerr << "Case ID must be between 0 and " << case_count << '\n';
        return 2;
    }
    try {
        simulate(id, argv[2]);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
