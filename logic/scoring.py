def add_score(scores, question, choice):
    if not scores:
        scores = {}

    # options 구조:
    # "A": ("텍스트", {"R": 5, "A": 2})
    _, trait_scores = question["options"].get(choice, (None, {}))

    for trait, value in trait_scores.items():
        scores[trait] = scores.get(trait, 0) + value

    return scores
