#include "antennasim/fields.hpp"

namespace antennasim {

FieldStorage::FieldStorage(UniformGrid grid) : grid_(grid) {
    for (std::size_t id = 0; id < fields_.size(); ++id) {
        const auto component = static_cast<FieldComponent>(id);
        fields_[id].resize(grid_.layout(component).element_count, 0.0);
    }
}

double& FieldStorage::at(FieldComponent component, std::array<std::size_t, 3> index) {
    const auto offset = grid_.offset(component, index);
    return fields_[static_cast<std::size_t>(component)][offset];
}

const double& FieldStorage::at(
    FieldComponent component, std::array<std::size_t, 3> index) const {
    const auto offset = grid_.offset(component, index);
    return fields_[static_cast<std::size_t>(component)][offset];
}

std::span<const double> FieldStorage::values(FieldComponent component) const {
    (void)grid_.layout(component);
    return fields_[static_cast<std::size_t>(component)];
}

} // namespace antennasim
