import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def ocr(image: str) -> None:
    raise NotImplementedError("OCR pipeline not implemented yet")


@app.command()
def reconstruct(image: str) -> None:
    raise NotImplementedError("Reconstruction pipeline not implemented yet")


if __name__ == "__main__":
    app()
