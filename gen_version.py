from version import __version_base__, __date_stamp__, build_number

a, b, c = __version_base__.split(".")
ver = f"{__version_base__}-{__date_stamp__}"

with open("version_info.template.txt", encoding="utf-8") as f:
    tpl = f.read()

out = tpl.format(a=a, b=b, c=c, build=build_number(), ver=ver)

with open("version_info.txt", "w", encoding="utf-8") as f:
    f.write(out)

print(f"version_info.txt -> {ver} (build={build_number()})")
