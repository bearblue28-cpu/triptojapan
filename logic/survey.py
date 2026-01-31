def add_score(scores, question, choice):
    for trait, value in question["options"][choice][1].items():
        scores[trait] = scores.get(trait, 0) + value
    return scores
