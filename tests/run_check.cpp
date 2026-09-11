#include "reference.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <string_view>

namespace {
using namespace antennasim;
using Index = std::array<std::size_t,3>;
std::size_t checks = 0;
void check(bool condition, std::string_view context) {
    ++checks;
    if (!condition) throw std::runtime_error(std::string(context));
}
template<class Function> void rejects(Function function, std::string_view context) {
    bool rejected = false;
    try { function(); } catch (const std::exception&) { rejected = true; }
    check(rejected,context);
}
void source_and_probe() {
    const UniformGrid grid{CellCounts{5,4,3},{2,3,5}};
    const auto dt = VacuumTimeStep::from_seconds(grid,1e-9);
    const FieldStorage zero{grid};
    const Index edge{2,2,1};
    for (std::size_t id = 0; id < 3; ++id) for (double sign : {-1.,1.}) {
        const auto f = static_cast<FieldComponent>(id);
        const ElectricCurrent current{grid,{{f,edge,sign*.25}}};
        ReferenceStepper solver{zero,dt};
        solver.step(current);
        const double expected = -1e-9*sign*.25/epsilon0;
        const auto signed_probe = sample_probe(solver,{f,edge});
        check(signed_probe.value == solver.fields().at(f,edge) && signed_probe.value*sign < 0,
              "probe preserves signed driven value");
        for (std::size_t other = 0; other < 6; ++other) {
            const auto g = static_cast<FieldComponent>(other);
            const auto target = grid.offset(f,edge);
            const auto values = solver.fields().values(g);
            for (std::size_t offset = 0; offset < values.size(); ++offset) {
                const double answer = other == id && offset == target ? expected : 0;
                check(std::abs(values[offset]-answer)/std::max(1.,std::abs(answer)) <= 1e-13,"S06 source sign/all samples");
            }
        }
        // Independently reconstruct charge at the two interior endpoint nodes.
        auto upper_node = edge; ++upper_node[id];
        for (const auto node : {edge,upper_node}) {
            auto low = node; --low[id];
            const double rho = epsilon0*(solver.fields().at(f,node)-solver.fields().at(f,low))/grid.spacing_m()[id];
            const double delta = (node == edge ? -1 : 1)*1e-9*sign*.25/grid.spacing_m()[id];
            check(std::abs(rho-delta) <= 1e-13*std::abs(delta),"discrete impressed-current continuity");
        }
        solver.step();
        check(!solver.failed() && solver.state_index() == 2,"charged state continues source-free");
    }
    ReferenceStepper empty{zero,dt}, driven_empty{zero,dt};
    const ElectricCurrent empty_current{grid,{}};
    for (std::uint64_t n = 0; n < 3; ++n) {
        for (std::size_t id = 0; id < 6; ++id) {
            const auto f = static_cast<FieldComponent>(id);
            const auto sample = sample_probe(empty,{f,edge});
            check(sample.state == n && sample.value == 0,"native state/value");
            const double time = (static_cast<double>(n)-(id < 3 ? 0 : .5))*1e-9;
            check(std::abs(sample.time_s-time) <= 5e-15*std::max(std::abs(time),1e-9),"S07 native time including negative H");
            for (std::size_t a = 0; a < 3; ++a) {
                const double half = (id < 3 ? id == a : id-3 != a) ? .5 : 0;
                const double expected = (static_cast<double>(edge[a])+half)*std::array{2.,3.,5.}[a];
                check(sample.position_m[a] == expected,"S07 independent native position");
                auto outside = edge; outside[a] = grid.layout(f).extents[a];
                rejects([&] { (void)sample_probe(empty,{f,outside}); },"invalid probe each component/axis");
            }
        }
        if (n < 2) { empty.step(); driven_empty.step(empty_current); }
    }
    for (std::size_t id = 0; id < 6; ++id) {
        const auto f = static_cast<FieldComponent>(id);
        for (std::size_t axis = 0; axis < 3; ++axis) {
            auto outside = edge; outside[axis] = grid.layout(f).extents[axis];
            rejects([&] { ElectricCurrent invalid{grid,{{f,outside,1}}}; },"out-of-range current");
        }
        if (id >= 3) rejects([&] { ElectricCurrent invalid{grid,{{f,edge,1}}}; },"H source unsupported");
        else {
            for (std::size_t axis = 0; axis < 3; ++axis) if (axis != id) {
                for (auto face : {std::size_t{0},grid.cells().values()[axis]}) {
                    auto at = edge; at[axis] = face;
                    rejects([&] { ElectricCurrent invalid{grid,{{f,at,1}}}; },"boundary current");
                }
            }
            for (double value : {std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})
                rejects([&] { ElectricCurrent invalid{grid,{{f,edge,value}}}; },"nonfinite source");
            rejects([&] { ElectricCurrent invalid{grid,{{f,edge,1},{f,edge,2}}}; },"duplicate current target");
            ReferenceStepper overflow{zero,dt};
            ElectricCurrent huge{grid,{{f,edge,std::numeric_limits<double>::max()}}};
            bool located = false;
            try { overflow.step(huge); } catch (const FieldUpdateError& error) {
                located = error.step() == 0 && error.component() == f && error.index() == edge;
            }
            check(located && overflow.failed() && overflow.state_index() == 0,"located terminal source overflow");
            rejects([&] { (void)overflow.fields(); },"failed field read");
            rejects([&] { overflow.step(); },"failed restart");
            FieldStorage charged{grid}; charged.at(f,edge) = 1;
            rejects([&] { ReferenceStepper invalid{charged,dt}; },"initial rho=0 screening retained");
        }
    }
    ReferenceStepper mismatch{zero,dt};
    const UniformGrid different{CellCounts{6,4,3},{2,3,5}};
    ElectricCurrent wrong{different,{}};
    rejects([&] { mismatch.step(wrong); },"source grid mismatch");
    // Preflight increments are finite; adding one to an already large E must
    // still fail after mutation with the original input-state location.
    FieldStorage loop{grid};
    const double amplitude = std::numeric_limits<double>::max()/8;
    loop.at(FieldComponent::Ex,{1,1,1}) = amplitude;
    loop.at(FieldComponent::Ex,{1,2,1}) = -amplitude;
    loop.at(FieldComponent::Ey,{2,1,1}) = amplitude*1.5;
    loop.at(FieldComponent::Ey,{1,1,1}) = -amplitude*1.5;
    ReferenceStepper addition_overflow{loop,dt};
    ElectricCurrent finite_increment{grid,{{FieldComponent::Ex,{1,1,1},-std::numeric_limits<double>::max()/dt.e_scale()*.99}}};
    bool located = false;
    try { addition_overflow.step(finite_increment); } catch (const FieldUpdateError& error) {
        located = error.step() == 0 && error.component() == FieldComponent::Ex && error.index() == Index{1,1,1};
    }
    check(located && addition_overflow.failed() && addition_overflow.state_index() == 0,"terminal current addition overflow after mutation");
    rejects([&] { (void)addition_overflow.times(); },"failed native time read");
    ReferenceStepper nan{zero,dt};
    rejects([&] { nan.step(empty_current,std::numeric_limits<double>::quiet_NaN()); },"nonfinite scale");
    for (const auto text : {"", "0", "-1", "+1", "1.5", " 2", "2 ", "1e2", "NaN", "18446744073709551616", "4503599627370496"})
        rejects([&] { (void)parse_steps(text); },"strict run count parsing");
    check(parse_steps("002") == 2 && parse_steps("4503599627370495") == 4503599627370495ULL,"valid unsigned counts");
    rejects([&] { validate_run_steps(dt,0); },"zero duration");
    rejects([&] { validate_run_steps(dt,std::numeric_limits<std::uint64_t>::max()); },"unrepresentable duration");
    for (std::size_t id = 0; id < 6; ++id)
        check(std::ranges::equal(empty.fields().values(static_cast<FieldComponent>(id)),driven_empty.fields().values(static_cast<FieldComponent>(id))),"empty current preserves source-free path");
}
void fixtures() {
    const auto propagation = benchmark::cases("propagation");
    const auto stability = benchmark::cases("stability");
    check(propagation.size() == 36 && stability.size() == 4,"fixed suite enumeration");
    double max_div = 0, max_plateau = 0;
    // All six orientations on the primary p24 grid; larger guards/counts above
    // require no allocations. Larger fixture execution remains REF-05 evidence.
    for (const auto& config : propagation) {
        if (config.p != 24 || config.name.find("primary") == std::string::npos) continue;
        FieldStorage fields{config.grid};
        const auto result = benchmark::initialize(config,fields);
        max_div = std::max(max_div,result.divergence);
        max_plateau = std::max(max_plateau,result.plateau);
        ReferenceStepper solver{fields,config.dt};
        check(solver.state_index() == 0,"S08 production initialization screening");
    }
    for (const auto& config : stability) {
        FieldStorage fields{config.grid};
        const auto result = benchmark::initialize(config,fields);
        max_div = std::max(max_div,result.divergence);
        ReferenceStepper solver{fields,config.dt};
        check(solver.state_index() == 0,"V03 shape screening");
    }
    rejects([] { (void)benchmark::cases("smoke",9); },"isolation guard before allocation");
    rejects([] { (void)benchmark::cases("unknown"); },"unknown suite");
    std::cout << "S08 maximum normalized divergence=" << max_div << " plateau=" << max_plateau << '\n';
}
} // namespace
int main() {
    try { source_and_probe(); fixtures(); std::cout << "PASS " << checks << " run/source/probe checks\n"; return 0; }
    catch (const std::exception& error) { std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1; }
}
