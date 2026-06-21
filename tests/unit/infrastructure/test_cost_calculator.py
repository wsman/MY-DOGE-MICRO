from doge.infrastructure.llm.cost_calculator import CostCalculator, ModelPricing


def test_cost_calculator_accounts_for_cached_tokens():
    calculator = CostCalculator({
        "kimi-test": ModelPricing(
            prompt_per_million_usd=1.0,
            cached_prompt_per_million_usd=0.1,
            completion_per_million_usd=2.0,
        )
    })

    cost = calculator.calculate_cost(
        model="kimi-test",
        prompt_tokens=1000,
        cached_tokens=400,
        completion_tokens=100,
    )

    assert cost == 0.00084
