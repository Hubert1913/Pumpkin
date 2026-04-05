use crate::propagators::nogoods::NogoodDeletionMethod;
use crate::propagators::nogoods::NogoodOrderingMetric;

/// Options related to nogood management, i.e., how and when to remove learned nogoods from the
/// database.
#[derive(Debug, Copy, Clone)]
pub struct LearningOptions {
    /// Determines when to rescale the activites of the learned nogoods in the database.
    pub max_activity: f32,
    /// Determines the factor by which the activities are divided when a conflict is found.
    pub activity_decay_factor: f32,
    /// The maximum number of nogoods that the solver initially sotres
    pub max_num_nogoods: usize,
    /// The percentage by which we increase maximal number of nogoods after each database reduction
    pub max_num_nogoods_bump: f32,
    /// Specifies by how much the activity is increased when a nogood is bumped.
    pub activity_bump_increment: f32,
    pub nogood_deletion_method: NogoodDeletionMethod,
    pub first_nogood_ordering_metric: NogoodOrderingMetric,
    pub second_nogood_ordering_metric: NogoodOrderingMetric,
}
impl Default for LearningOptions {
    fn default() -> Self {
        Self {
            max_activity: 1e20,
            activity_decay_factor: 0.99,
            max_num_nogoods: 40000,
            max_num_nogoods_bump: 1.1,
            activity_bump_increment: 1.0,
            nogood_deletion_method: NogoodDeletionMethod::Single,
            first_nogood_ordering_metric: NogoodOrderingMetric::LBD,
            second_nogood_ordering_metric: NogoodOrderingMetric::Activity,
        }
    }
}
