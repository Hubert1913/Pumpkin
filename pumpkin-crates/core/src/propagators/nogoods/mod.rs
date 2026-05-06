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
    /// Uses three metrics (all but constraints count), keep nogoods that are good according to at least one
    AllEitherExceptCc,
    /// Removes nogoods randomly (only the ones which aren't currently propagating)
    Random,
    /// Behaves in an opposite way to the best found scheme (either_lbd_activity)
    /// Thus it removes the nogoods with either highest LBD or highest activity
    Opposite,
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
pub enum NogoodOrderingMetric {
    #[default]
    LBD,
    Activity,
    NumberVariables,
    ConstraintsCount,
}
