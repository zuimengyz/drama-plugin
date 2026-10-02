"""Execution route/prerequisite planning; no artistic decisions or provider calls."""
from drama_plugin.creative_engine.contracts import DependencyTask, RoutePlan, RouteRequest


class RouteSelector:
    def plan(self, request: RouteRequest) -> RoutePlan:
        required = {"text_to_video": (), "image_to_video": ("first_frame",),
                    "reference_video": ("character_reference", "environment_reference"), "audio": ()}[request.input_mode]
        missing = tuple(item for item in required if item not in request.available_inputs)
        tasks = tuple(DependencyTask(task_id=item, output="image", estimated_cost=request.estimated_child_cost)
                      for item in missing)
        return RoutePlan(route=request.input_mode, tasks=(DependencyTask(task_id="goal", output=request.output,
            requires=missing), *tasks), capability_available=request.input_mode in request.available_capabilities,
            authorization_required=bool(sum(t.estimated_cost for t in tasks)), cost_limit=request.cost_limit)
