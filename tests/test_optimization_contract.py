import json

from pga_shootout.optimization_contract import OptimizationRequest, optimization_examples


def test_contract_round_trips_and_examples_share_one_generic_shape():
    examples = optimization_examples("catalog-v1")
    assert len(examples) == 8
    for example in examples:
        payload = json.loads(json.dumps(example.to_dict()))
        assert OptimizationRequest.from_dict(payload) == example
        assert "mode" not in payload
        assert set(payload) == {"schema_version", "request_id", "provenance", "scope", "constraints", "objectives", "comparison_policy", "uncertainty_policy"}


def test_examples_cover_constraints_scenarios_pareto_and_honest_missing_data():
    examples = optimization_examples("catalog-v1")
    assert any(item.constraints for item in examples)
    assert any(len(item.scope.scenarios) > 1 for item in examples)
    assert any(item.comparison_policy == "pareto_retain_all" for item in examples)
    assert any("validated_carry_model" in constraint.required_data for item in examples for constraint in item.constraints)

