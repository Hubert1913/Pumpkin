mod arena_allocator;
mod checker;
mod learning_options;
mod nogood_id;
mod nogood_info;
mod nogood_propagator;

pub use checker::*;
use clap::ValueEnum;
pub use learning_options::*;
pub(crate) use nogood_id::*;
pub(crate) use nogood_info::*;
pub(crate) use nogood_propagator::*;

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
pub enum NogoodDeletionMethod {
    /// Use only one metric for nogood ordering
    #[default]
    Single,
    /// Use two metrics, keep nogoods that are good according to both metrics
    DoubleBoth,
    /// Use two metrics, keep nogoods that are good according to either of the metrics
    DoubleEither,
    /// Uses all four metrics, keep nogoods that are good according to all of them
    All,
    /// Uses all four metrics, keep nogoods that are good according to at least one
    AllEither,
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
pub enum NogoodOrderingMetric {
    #[default]
    LBD,
    Activity,
    NumberVariables,
    ConstraintsCount,
}
