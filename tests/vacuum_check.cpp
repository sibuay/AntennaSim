#include "antennasim/vacuum.hpp"
#include "antennasim/detail/vacuum_kernel.hpp"
#include "reference_steps_golden.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string_view>
#include <type_traits>

namespace {
using namespace antennasim;
using enum FieldComponent;
using Index = std::array<std::size_t, 3>;
using Position = std::array<double, 3>;
constexpr std::array components{Ex, Ey, Ez, Hx, Hy, Hz};
constexpr double infinity = std::numeric_limits<double>::infinity();
constexpr double tiny = std::numeric_limits<double>::denorm_min();
constexpr double nan = std::numeric_limits<double>::quiet_NaN();
std::size_t checks = 0;
std::size_t failures = 0;
double max_increment_error = 0;
double max_golden_error = 0;
double max_divergence_error = 0;
double max_adjoint_error = 0;

static_assert(!std::is_copy_constructible_v<ReferenceStepper>);
static_assert(!std::is_move_constructible_v<ReferenceStepper>);
static_assert(std::is_same_v<decltype(std::declval<ReferenceStepper&>().fields()), const FieldStorage&>);

void check(bool condition, std::string_view context) {
    ++checks;
    if (!condition) { ++failures; std::cerr << "FAIL: " << context << '\n'; }
}
template <class Error, class Function>
void rejects(Function function, std::string_view context) {
    try { function(); check(false, context); }
    catch (const Error&) { check(true, context); }
    catch (const std::exception& error) {
        check(false, context); std::cerr << "Wrong error: " << error.what() << '\n';
    }
}
template <class Function>
void enumerate(Index shape, Function function) {
    for (std::size_t k = 0; k < shape[2]; ++k)
        for (std::size_t j = 0; j < shape[1]; ++j)
            for (std::size_t i = 0; i < shape[0]; ++i) function(Index{i,j,k});
}
template <class Function>
void all(const UniformGrid& grid, Function function) {
    for (std::size_t id = 0; id < 6; ++id)
        enumerate(grid.layout(components[id]).extents, [&](Index index) { function(id, index); });
}
bool wall(const UniformGrid& grid, std::size_t id, Index index) {
    // Independent native-coordinate test, not production wall classification.
    const auto p = grid.position_m(components[id], index);
    for (std::size_t a = 0; a < 3; ++a)
        if (p[a] == 0 || p[a] == grid.lengths_m()[a]) return true;
    return false;
}
bool active(const UniformGrid& grid, std::size_t id, Index index) {
    return id >= 3 || !wall(grid, id, index);
}
void load_golden(FieldStorage& fields, std::size_t stage = 0) {
    for (const auto& sample : reference_golden::samples)
        fields.at(components[sample.component], sample.index) = sample.stages[stage];
}
void compare_golden(const FieldStorage& fields, std::size_t stage) {
    for (const auto& sample : reference_golden::samples) {
        const auto expected = sample.stages[stage];
        const auto old = sample.stages[stage == 0 ? 0 : stage - 1];
        const auto scale = std::max(1.0, std::abs(old) + std::abs(expected - old));
        const auto error = std::abs(fields.at(components[sample.component], sample.index) - expected) / scale;
        max_golden_error = std::max(max_golden_error, error);
        check(error <= 1e-13, "exact-rational half/full-stage comparator");
        if (wall(fields.grid(), sample.component, sample.index))
            check(fields.at(components[sample.component], sample.index) == 0, "exact E/normal H wall preservation");
    }
}

void time_step_policy() {
    for (const Position spacing : {Position{2,2,2}, Position{2,3,5}, Position{0.01,0.015,0.02}}) {
        const UniformGrid grid{CellCounts{2,3,4}, spacing};
        const double inverse_sum = 1/(spacing[0]*spacing[0]) + 1/(spacing[1]*spacing[1]) +
                                   1/(spacing[2]*spacing[2]);
        const double reference = 1 / (299792458.0 * std::sqrt(inverse_sum));
        for (double q : {0.5, 0.99}) {
            const auto dt = VacuumTimeStep::from_courant(grid, q);
            check(std::abs(dt.seconds()/(q*reference)-1) <= 5e-15, "independent CFL formula");
            check(std::abs(dt.courant_fraction()/q-1) <= 5e-15, "actual Courant fraction");
            check(dt.e_scale() > 0 && dt.h_scale() > 0, "positive update scales");
        }
        const auto dt = VacuumTimeStep::from_courant(grid);
        check(std::abs(dt.seconds()/(0.99*reference)-1) <= 5e-15, "default Courant fraction");
        for (double bad : {0.0, -0.1, 1.0, 1.1, nan, infinity, -infinity})
            rejects<std::invalid_argument>([&] { (void)VacuumTimeStep::from_courant(grid, bad); }, "invalid q");
        for (double bad : {0.0, -1.0, nan, infinity, -infinity, dt.limit_seconds(),
                           std::nextafter(dt.limit_seconds(), infinity)})
            rejects<std::invalid_argument>([&] { (void)VacuumTimeStep::from_seconds(grid, bad); }, "invalid explicit dt");
        const double below = std::nextafter(dt.limit_seconds(), 0.0);
        check(VacuumTimeStep::from_seconds(grid, below).seconds() == below, "next-below CFL accepted unchanged");
        check(dt.times_at(0).e_s == 0 && dt.times_at(0).h_s == -dt.seconds()/2, "native n=0 times");
        check(dt.times_at(1).e_s == dt.seconds() && dt.times_at(1).h_s == dt.seconds()/2, "native n=1 times");
        check(dt.times_at(2).e_s == 2*dt.seconds() && dt.times_at(2).h_s == 1.5*dt.seconds(), "native n=2 times");
        rejects<std::overflow_error>([&] { (void)dt.times_at(std::uint64_t{1} << 52); }, "half index range");
        rejects<std::overflow_error>([&] { (void)dt.times_at(std::numeric_limits<std::uint64_t>::max()); }, "maximum state index");
        rejects<std::overflow_error>([&] { (void)VacuumTimeStep::from_courant(grid, tiny); }, "rounded-zero selected dt");
        rejects<std::overflow_error>([&] { (void)VacuumTimeStep::from_seconds(grid, tiny); }, "half-step underflow");
    }
    for (std::size_t a = 0; a < 3; ++a) {
        Position spacing{1,1,1};
        spacing[a] = 2*tiny;
        const UniformGrid denormal{CellCounts{2,2,2}, spacing};
        rejects<std::overflow_error>([&] { (void)VacuumTimeStep::from_courant(denormal); }, "denormal CFL underflow");
        spacing = {1e307,1e307,1e307};
        const UniformGrid huge{CellCounts{2,2,2}, spacing};
        rejects<std::overflow_error>([&] { (void)VacuumTimeStep::from_courant(huge); }, "electric scale overflow");
        spacing = {1,1,1}; spacing[a] = 1e300;
        const UniformGrid disparate{CellCounts{2,2,2}, spacing};
        rejects<std::overflow_error>([&] { (void)VacuumTimeStep::from_seconds(disparate, 1e-320); }, "derivative coefficient underflow");
    }
    const UniformGrid large{CellCounts{2,2,2}, {1e305,1e305,1e305}};
    const auto dt_large = VacuumTimeStep::from_courant(large, 0.5);
    rejects<std::overflow_error>([&] { (void)dt_large.times_at(1000000000000000ULL); }, "timestamp multiplication overflow");
    const UniformGrid grid{CellCounts{5,4,3}, {2,3,5}};
    const auto dt = VacuumTimeStep::from_seconds(grid, 1e-9);
    // Independent floating-point event ordering at the allowed index limit.
    constexpr auto n = (std::uint64_t{1} << 52) - 1;
    const double nd = static_cast<double>(n);
    const bool ordered = (nd-1)*1e-9 < (nd-0.5)*1e-9 && (nd-0.5)*1e-9 < nd*1e-9;
    if (!ordered) rejects<std::overflow_error>([&] { (void)dt.times_at(n); }, "merged timestamps");
    else check(dt.times_at(n).h_s < dt.times_at(n).e_s, "large representable timestamps");
    FieldStorage initial{grid}; load_golden(initial);
    ReferenceStepper smoke{initial, VacuumTimeStep::from_courant(grid, 1 - 0x1p-20)};
    smoke.step();
    check(smoke.state_index() == 1 && !smoke.failed(), "near-CFL one-step finite smoke");
}

void local_affine() {
    const UniformGrid grid{CellCounts{5,4,3}, {2,3,5}};
    const auto dt = VacuumTimeStep::from_seconds(grid, 1e-9);
    constexpr std::array<Position, 3> slopes{{{2,3,5}, {7,11,13}, {17,19,23}}};
    constexpr Position curl{6,-12,4};
    // Both families, all nine source/derivative pairs, both slope signs.
    // Six nonzero curls per family include the twelve signed FND-03 terms.
    for (bool electric_source : {false, true}) {
        for (int source = -2; source < 3; ++source) {
            const int axes = source < 0 ? 1 : 3;
            for (int a = 0; a < axes; ++a) for (const double sign : {-1.0, 1.0}) {
                FieldStorage fields{grid};
                all(grid, [&](std::size_t id, Index index) {
                    if ((id < 3) != electric_source) return;
                    const auto p = grid.position_m(components[id], index);
                    double value = 0;
                    if (source == -2) value = 7; // Constant vector.
                    else if (source == -1)
                        for (std::size_t b = 0; b < 3; ++b) value += slopes[id%3][b]*p[b];
                    else if (id%3 == static_cast<std::size_t>(source)) value = p[static_cast<std::size_t>(a)];
                    fields.at(components[id], index) = sign*value;
                });
                const auto expected_curl = [&](std::size_t t) {
                    if (source == -2) return 0.0;
                    if (source == -1) return sign*curl[t];
                    // Independent continuous cross product of derivative axis and source axis.
                    constexpr int epsilon[3][3][3] = {
                        {{0,0,0},{0,0,1},{0,-1,0}},
                        {{0,0,-1},{0,0,0},{1,0,0}},
                        {{0,1,0},{-1,0,0},{0,0,0}}};
                    return sign*epsilon[t][a][source];
                };
                all(grid, [&](std::size_t id, Index index) {
                    if ((id < 3) == electric_source || !active(grid,id,index)) return;
                    const double expected = expected_curl(id%3);
                    check(detail::curl_at(fields,components[id],index) == expected, "exact local affine/constant curl");
                });
                if (electric_source) detail::advance_h(fields,dt,0);
                else detail::advance_e(fields,dt,0);
                all(grid, [&](std::size_t id, Index index) {
                    if ((id < 3) == electric_source || !active(grid,id,index)) return;
                    const double expected = expected_curl(id%3)*(electric_source ? -dt.h_scale() : dt.e_scale());
                    const double actual = fields.at(components[id],index);
                    const double error = std::abs(actual-expected)/std::max(1.0,std::abs(expected));
                    max_increment_error = std::max(max_increment_error,error);
                    check(error <= 1e-13, "signed derivative update increment");
                    if (expected == 0) check(actual == 0, "absent derivative exactly zero");
                });
            }
        }
    }
}

void polynomial_divergence() {
    const UniformGrid grid{CellCounts{5,4,3}, {2,3,5}};
    FieldStorage fields{grid}; FieldStorage curls{grid};
    all(grid,[&](std::size_t id, Index index) {
        const auto [x,y,z] = grid.position_m(components[id],index);
        const Position g{x*x*y+z*z*z, y*y*z+x*x*x, z*z*x+y*y*y};
        fields.at(components[id],index) = g[id%3];
    });
    all(grid,[&](std::size_t id, Index index) {
        if (!active(grid,id,index)) return;
        const auto p = grid.position_m(components[id],index);
        const auto a = (id%3+1)%3;
        // Exact rational centered cubic derivative: 3*x^2+d^2/4, minus x^2.
        const double expected = 2*p[a]*p[a] + grid.spacing_m()[a]*grid.spacing_m()[a]/4;
        const double actual = detail::curl_at(fields,components[id],index);
        check(actual == expected, "exact polynomial centered difference");
        curls.at(components[id],index) = actual;
    });
    for (bool electric : {true,false}) {
        enumerate(grid.cells().values(),[&](Index index) {
            if (electric && (index[0]==0 || index[1]==0 || index[2]==0)) return;
            double divergence = 0;
            double magnitude = 0;
            for (std::size_t a = 0; a < 3; ++a) {
                auto high = index; auto low = index;
                if (electric) --low[a]; else ++high[a];
                const auto component = components[a+(electric ? 0U : 3U)];
                const double term = (curls.at(component,high)-curls.at(component,low))/grid.spacing_m()[a];
                divergence += term; magnitude += std::abs(term);
            }
            const double error = std::abs(divergence)/std::max(1.0,magnitude);
            max_divergence_error = std::max(max_divergence_error,error);
            check(error <= 1e-12,"divergence of production curl");
        });
    }
    rejects<std::out_of_range>([&] { (void)detail::curl_at(fields,Ex,{0,0,0}); }, "wall rejected before backward subtraction");
    rejects<std::invalid_argument>([&] { (void)detail::curl_at(fields,static_cast<FieldComponent>(255),{}); }, "invalid curl selector");
}

void adjoint() {
    for (const Index counts : {Index{2,3,4},Index{5,4,3}}) {
        const UniformGrid grid{CellCounts{counts[0],counts[1],counts[2]}, {2,3,5}};
        FieldStorage fields{grid};
        all(grid,[&](std::size_t id,Index index) {
            const int value = static_cast<int>((17*index[0]+31*index[1]+43*index[2]+13*id)%101)-50;
            fields.at(components[id],index) = wall(grid,id,index) ? 0 : value;
        });
        std::array<double,2> dots{};
        double magnitude = 0;
        all(grid,[&](std::size_t id,Index index) {
            if (!active(grid,id,index)) return;
            const auto p = grid.position_m(components[id],index);
            double weight = 1;
            for (std::size_t a = 0; a < 3; ++a)
                if (p[a] == 0 || p[a] == grid.lengths_m()[a]) weight *= 0.5;
            const double term = weight*fields.at(components[id],index)*detail::curl_at(fields,components[id],index);
            dots[id<3 ? 0U : 1U] += term; magnitude += std::abs(term);
        });
        const double reference = counts[0] == 2 ? -52411.0/30 : -27929.0/6;
        const double error = std::abs(dots[0]-dots[1])/std::max(1.0,magnitude);
        max_adjoint_error = std::max(max_adjoint_error,error);
        check(error <= 1e-12,"weighted adjoint production operators");
        check(std::abs(dots[0]-reference)/std::abs(reference) <= 1e-12 &&
              std::abs(dots[1]-reference)/std::abs(reference) <= 1e-12,"independent exact adjoint dot values");
    }
}

void stages_and_boundary() {
    const UniformGrid grid{CellCounts{5,4,3}, {2,3,5}};
    const auto dt = VacuumTimeStep::from_seconds(grid,1e-9);
    FieldStorage initial{grid}; load_golden(initial);
    FieldStorage local{grid}; load_golden(local);
    ReferenceStepper solver{initial,dt};
    initial.at(Ex,{1,1,1}) = 777; // Explicit initial copy; no borrowed mutable fields.
    compare_golden(solver.fields(),0);
    for (std::size_t n = 0; n < 2; ++n) {
        detail::advance_h(local,dt,n); compare_golden(local,2*n+1);
        detail::advance_e(local,dt,n); compare_golden(local,2*n+2);
        solver.step(); compare_golden(solver.fields(),2*n+2);
        check(solver.state_index() == n+1,"full-step state advances once");
        check(solver.times().e_s == dt.times_at(n+1).e_s && solver.times().h_s == dt.times_at(n+1).h_s,"stepper native times");
    }
    for (const Index counts : {Index{2,2,2},Index{2,3,4},Index{5,4,3}}) {
        const UniformGrid small{CellCounts{counts[0],counts[1],counts[2]}, {2,3,5}};
        FieldStorage zero{small};
        ReferenceStepper zero_solver{zero,VacuumTimeStep::from_courant(small)};
        for (int n = 0; n < 100; ++n) zero_solver.step();
        all(small,[&](std::size_t id,Index index) {
            check(zero_solver.fields().at(components[id],index) == 0,"100-step exact zero preservation/all actual ranges");
        });
    }
}

void input_and_failure() {
    const UniformGrid grid{CellCounts{5,4,3}, {2,3,5}};
    const auto dt = VacuumTimeStep::from_seconds(grid,1e-9);
    FieldStorage fields{grid};
    for (std::size_t id = 0; id < 6; ++id) {
        for (double bad : {nan,infinity,-infinity}) {
            fields.at(components[id],{1,1,1}) = bad;
            rejects<std::invalid_argument>([&] { ReferenceStepper run{fields,dt}; },"nonfinite initial field in each component");
        }
        fields.at(components[id],{1,1,1}) = 1;
        rejects<std::invalid_argument>([&] { ReferenceStepper run{fields,dt}; },"nonzero initial divergence in each component");
        fields.at(components[id],{1,1,1}) = 0;
    }
    all(grid,[&](std::size_t id,Index index) {
        if (!wall(grid,id,index)) return;
        fields.at(components[id],index) = 1;
        rejects<std::invalid_argument>([&] { ReferenceStepper run{fields,dt}; },"incompatible initial wall, every native wall sample");
        check(fields.at(components[id],index) == 1,"invalid initial data not silently clamped");
        fields.at(components[id],index) = 0;
    });
    const UniformGrid different{CellCounts{5,4,3}, {3,2,5}};
    const auto other = VacuumTimeStep::from_courant(different);
    rejects<std::invalid_argument>([&] { ReferenceStepper run{fields,other}; },"stepper spacing mismatch");
    rejects<std::invalid_argument>([&] { detail::advance_h(fields,other,0); },"H kernel spacing mismatch");
    rejects<std::invalid_argument>([&] { detail::advance_e(fields,other,0); },"E kernel spacing mismatch");
    // Independent H=curl(Ez potential impulse), finite and solenoidal.
    // E=0 leaves H unchanged; dt/epsilon0 times curl H overflows at Ex[1,2,1].
    fields.at(Hx,{2,1,1}) = 1e307;
    fields.at(Hx,{2,2,1}) = -1e307;
    fields.at(Hy,{1,2,1}) = -1.5e307;
    fields.at(Hy,{2,2,1}) = 1.5e307;
    ReferenceStepper failure{fields,dt};
    try { failure.step(); check(false,"nonfinite update must throw"); }
    catch (const FieldUpdateError& error) {
        check(error.step() == 0 && error.component() == Ex && error.index() == Index{1,2,1},"precise nonfinite update diagnostic");
    }
    check(failure.failed() && failure.state_index() == 0,"failed partial step not counted");
    rejects<std::logic_error>([&] { failure.step(); },"failed stepper cannot resume");
    rejects<std::logic_error>([&] { (void)failure.fields(); },"failed fields cannot be reported as a state");
    rejects<std::logic_error>([&] { (void)failure.times(); },"failed timestamps unavailable");
}
} // namespace

int main() {
    try {
        time_step_policy(); local_affine(); polynomial_divergence(); adjoint();
        stages_and_boundary(); input_and_failure();
    } catch (const std::exception& error) {
        std::cerr << "Unexpected exception: " << error.what() << '\n'; return 1;
    }
    std::cout << checks << " vacuum-kernel checks, " << failures << " failures.\n"
              << std::setprecision(17) << "Max normalized errors: increment=" << max_increment_error
              << " golden=" << max_golden_error << " divcurl=" << max_divergence_error
              << " adjoint=" << max_adjoint_error << '\n'
              << "LIMIT: structural/equation-level evidence; physical V01-V03 remain pending.\n";
    return failures == 0 ? 0 : 1;
}
