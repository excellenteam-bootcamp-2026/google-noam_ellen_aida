from autocomplete import cli
from autocomplete.models import AutoCompleteData


def test_format_completion_includes_all_result_fields() -> None:
    result = AutoCompleteData("A sentence", "source.txt", 7, 18)

    assert cli.format_completion(result) == (
        "A sentence (source.txt:7) [score: 18]"
    )


def test_display_completions_numbers_results(capsys) -> None:
    results = [
        AutoCompleteData("First", "a.txt", 0, 10),
        AutoCompleteData("Second", "b.txt", 1, 8),
    ]

    cli.display_completions(results)

    assert capsys.readouterr().out.splitlines() == [
        "1. First (a.txt:0) [score: 10]",
        "2. Second (b.txt:1) [score: 8]",
    ]


def test_display_completions_handles_empty_results(capsys) -> None:
    cli.display_completions([])

    assert capsys.readouterr().out == "No completions found.\n"


def test_cli_accumulates_input_and_resets(monkeypatch, capsys) -> None:
    entered_values = iter(["to be", " or not", "#"])
    searched_prefixes: list[str] = []

    def fake_input(prompt: str) -> str:
        try:
            return next(entered_values)
        except StopIteration as error:
            raise EOFError from error

    def fake_search(prefix: str) -> list[AutoCompleteData]:
        searched_prefixes.append(prefix)
        return []

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(cli, "get_best_k_completions", fake_search)

    cli.run_cli()

    assert searched_prefixes == ["to be", "to be or not"]
    assert "Query reset.\n" in capsys.readouterr().out


def test_cli_displays_service_errors(monkeypatch, capsys) -> None:
    entered_values = iter(["query"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(entered_values))
    monkeypatch.setattr(
        cli,
        "get_best_k_completions",
        lambda prefix: (_ for _ in ()).throw(
            RuntimeError("Autocomplete service has not been initialized")
        ),
    )

    cli.run_cli()

    assert capsys.readouterr().out == (
        "Error: Autocomplete service has not been initialized\n"
    )
