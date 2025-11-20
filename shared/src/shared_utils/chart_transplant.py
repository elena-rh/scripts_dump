from __future__ import annotations
from pathlib import Path
from typing import List
import zipfile, shutil



def _collect_chart_parts_to_replace(names: List[str]) -> List[str]:
    charts = [n for n in names if n.startswith("xl/charts/chart") and n.endswith(".xml")]
    chart_rels = [f"xl/charts/_rels/{Path(n).name}.rels" for n in charts]
    return charts + chart_rels

def transplant_charts(
    template_xlsx: str | Path,
    fresh_xlsx: str | Path,
    *,
    copy_colors_styles: bool = False,
    make_backup: bool = False,
) -> List[str]:
    """
    Recreates the fresh_xlsx with graph files copypasted from the template_xlsx file:
      - xl/charts/chart*.xml
      - xl/charts/_rels/chart*.xml.rels
    Optionally: xl/charts/colors*.xml e xl/charts/style*.xml

    This is useful when writing to existing xlsx file with the python library openpyxl
    which can mess up the chart rendering. By running this code with a sane template_xlsx
    the charts are guaranteed to render properly.

    Args:
        template_xlsx (str): The file path of the sane xlsx.
        fresh_xlsx (str): The file path of the xlsx where to fix graphs.
        copy_colors_styles (bool, optional): Whether to also copy palette and style files (usually not needed). Defaults to False.
        make_backup (bool, optional): Whether to make a backup of fresh_xlsx before updating it. Defaults to False.

    Returns:
        List[str]: the list of subsituted parts.
    """
    # as an aside, careful opening xlsx files with data_only=True, it breaks the formulas

    template_xlsx = Path(template_xlsx)
    fresh_xlsx    = Path(fresh_xlsx)

    replaced: List[str] = []
    tmp_path = fresh_xlsx.with_suffix(".tmp.xlsx")
    bak_path = fresh_xlsx.with_suffix(".bak.xlsx")

    # if there are residues from previous runs, try to clean up
    for p in (tmp_path,):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

    try:
        with zipfile.ZipFile(template_xlsx, "r") as zt, zipfile.ZipFile(fresh_xlsx, "r") as zd_old:
            fresh_names = zd_old.namelist()
            templ_names = set(zt.namelist())

            targets = _collect_chart_parts_to_replace(fresh_names)

            if copy_colors_styles:
                for n in fresh_names:
                    if n.startswith("xl/charts/colors") and n.endswith(".xml"):
                        targets.append(n)
                    if n.startswith("xl/charts/style") and n.endswith(".xml"):
                        targets.append(n)

            targets = sorted(set(targets))

            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zd_new:
                # write each entry only one time
                for name in fresh_names:
                    if name in targets and name in templ_names:
                        zd_new.writestr(name, zt.read(name))
                        replaced.append(name)
                    else:
                        zd_new.writestr(name, zd_old.read(name))

        if make_backup:
            try:
                shutil.move(fresh_xlsx, bak_path)
            except Exception:
                # avoid blocking the run but do not lose fresh_xlsx
                pass

        shutil.move(tmp_path, fresh_xlsx)

    finally:
        # cleanup
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass

    return replaced