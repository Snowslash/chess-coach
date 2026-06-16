from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, PatternSummary


def make_bundle(*, fen: str | None = "fen-1") -> AnalysisBundle:
    return AnalysisBundle(
        source_pgn="input/sample_games.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                site="https://lichess.org/abcdefgh",
                date="2026.06.04",
                white="TestPlayer",
                black="Opponent",
                result="1-0",
                player_colour="white",
                critical_moments=[
                    CriticalMoment(
                        game_id="g1",
                        move_number=12,
                        side="white",
                        san="Qh5",
                        phase="middlegame",
                        fen_before=fen,
                        eval_change=2.4,
                        classification="blunder",
                        best_move="Nf6",
                        note="Allowed a simple tactic.",
                    )
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1),
    )


def test_card_from_critical_moment_includes_fen_actual_best_and_prompt():
    from chess_coach.flashcards import cards_from_bundle

    cards = cards_from_bundle(make_bundle())

    assert cards[0].fen == "fen-1"
    assert cards[0].actual_move == "Qh5"
    assert cards[0].best_move == "Nf6"
    assert cards[0].theme == "tactical_blunder"
    assert "What cue" in cards[0].review_prompt


def test_cards_skip_moments_without_fen():
    from chess_coach.flashcards import cards_from_bundle

    assert cards_from_bundle(make_bundle(fen=None)) == []


def test_write_cards_markdown_contains_card_sections(tmp_path):
    from chess_coach.flashcards import cards_from_bundle, write_cards_markdown

    cards = cards_from_bundle(make_bundle())

    path = write_cards_markdown(cards, tmp_path / "cards.md")
    text = path.read_text(encoding="utf-8")

    assert "# Chess Coach Review Cards" in text
    assert "## Card 1" in text
    assert "FEN:" in text
    assert "Actual move:" in text
    assert "Best move:" in text
    assert "Review prompt" in text
