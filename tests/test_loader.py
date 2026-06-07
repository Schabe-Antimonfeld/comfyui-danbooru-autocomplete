from pathlib import Path
from textwrap import dedent

from core.loader import *


def test_to_display():
    assert to_display("natsusaki_yomi") == "natsusaki yomi"
    assert to_display("fate_(series)") == "fate \(series\)"

def test_load_txt(tmp_path):
    file = Path(tmp_path, "tags.txt")
    file.write_text(
        dedent('''\
            purple_pantyhose,0,7108\n
            kinomoto_sakura,4,7103\n
            ushio_(kancolle),4,7102\n
            idol_clothes,0,7100\n
            pink_cardigan,0,7096\n
            bad_count,abc,def\n
            missing_fields\n
            ,1,14514\n
        '''
        ),
        encoding="utf-8"
    )
    assert load_txt(str(file)) == [
        ("purple_pantyhose", "purple pantyhose", 0, 7108),
        ("kinomoto_sakura", "kinomoto sakura", 4, 7103),
        ("ushio_(kancolle)", "ushio \(kancolle\)", 4, 7102),
        ("idol_clothes", "idol clothes", 0, 7100),
        ("pink_cardigan", "pink cardigan", 0, 7096),
        ("bad_count", "bad count", 0, 0),
        ("missing_fields", "missing fields", 0, 0),
    ]

def test_load_csv(tmp_path):
    file = Path(tmp_path, "tags.csv")
    file.write_text(
        dedent('''\
            raw,category,count\n
            purple_pantyhose,0,7108\n
            kinomoto_sakura,4,7103\n
            ushio_(kancolle),4,7102\n
            idol_clothes,0,7100\n
            pink_cardigan,0,7096\n
            bad_count,abc,def\n
            missing_fields\n
            ,1,14514\n
        '''
        ),
        encoding="utf-8"
    )
    assert load_csv(str(file)) == [
        ("purple_pantyhose", "purple pantyhose", 0, 7108),
        ("kinomoto_sakura", "kinomoto sakura", 4, 7103),
        ("ushio_(kancolle)", "ushio \(kancolle\)", 4, 7102),
        ("idol_clothes", "idol clothes", 0, 7100),
        ("pink_cardigan", "pink cardigan", 0, 7096),
        ("bad_count", "bad count", 0, 0),
        ("missing_fields", "missing fields", 0, 0),
    ]

def test_load_tags_dir_missing(tmp_path):
    missing_dir = tmp_path / "missing"
    assert load_tags(str(missing_dir)) == []

def test_load_tags(tmp_path):
    txt = tmp_path / "a.txt"
    csv = tmp_path / "b.csv"

    txt.write_text(
        dedent('''\
            purple_pantyhose,0,7108\n
            kinomoto_sakura,4,7103\n
            ushio_(kancolle),4,7102\n
            idol_clothes,0,7100\n
            pink_cardigan,0,7096\n
            bad_count,abc,def\n
            missing_fields\n
            ,1,14514\n
        '''
        ),
        encoding="utf-8"
    )

    csv.write_text(
        dedent('''\
            raw,category,count\n
            purple_pantyhose,0,7103\n
            kinomoto_sakura,4,7103\n
            ushio_(kancolle),4,7102\n
            idol_clothes,0,7101\n
            pink_cardigan,0,7096\n
            bad_count,abc,def\n
            missing_fields\n
            ,1,14514\n
        '''
        ),
        encoding="utf-8"
    )

    result = load_tags(str(tmp_path))

    assert result == [
        ("purple_pantyhose", "purple pantyhose", 0, 7108),
        ("kinomoto_sakura", "kinomoto sakura", 4, 7103),
        ("ushio_(kancolle)", "ushio \(kancolle\)", 4, 7102),
        ("idol_clothes", "idol clothes", 0, 7101),
        ("pink_cardigan", "pink cardigan", 0, 7096),
        ("bad_count", "bad count", 0, 0),
        ("missing_fields", "missing fields", 0, 0),
    ]