"""Registro o teste antes de retreinar os modelos de uso."""


def test_predictions(models, x_test, test_features, matches, metrics):
    lookup = matches.set_index("id")
    results = {}
    for name, model in models.items():
        probabilities = model.predict_proba(x_test)
        rows = []
        for identifier, values in zip(test_features.id, probabilities):
            game = lookup.loc[identifier]
            p = dict(zip(model.classes_, map(float, values)))
            predicted = max(("A", "D", "H"), key=p.get)
            rows.append(
                {
                    "id": int(identifier),
                    "season": int(game.season),
                    "date": game.date,
                    "home": game.home_name,
                    "away": game.away_name,
                    "home_goals": int(game.hg),
                    "away_goals": int(game.ag),
                    "probabilities": p,
                    "predicted": predicted,
                    "actual": game.result,
                    "correct": predicted == game.result,
                }
            )
        hits = sum(row["correct"] for row in rows)
        results[name] = {
            "metrics": {
                "total": len(rows),
                "hits": hits,
                "errors": len(rows) - hits,
                **{field: metrics[name][field] for field in ("accuracy", "f1_macro", "log_loss")},
            },
            "matches": rows,
        }
    return results
