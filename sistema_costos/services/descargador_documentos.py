from pathlib import Path
from urllib.request import urlopen


class DescargadorDocumentos:
    MAX_BYTES = 25 * 1024 * 1024  # 25 MB

    def descargar_pdf(self, url: str, destino: Path) -> Path:
        with urlopen(url, timeout=60) as response:
            contenido = response.read(self.MAX_BYTES + 1)

        if len(contenido) > self.MAX_BYTES:
            raise ValueError("El documento supera el límite de 25 MB.")

        if not contenido.startswith(b"%PDF-"):
            raise ValueError(
                "La respuesta no tiene una cabecera PDF reconocible."
            )

        destino.parent.mkdir(parents=True, exist_ok=True)

        # No sobrescribe archivos existentes.
        with destino.open("xb") as archivo:
            archivo.write(contenido)

        return destino