"""Read-only portable CLI: python -m drama_plugin.characters REF VERSION [--route ...]."""
import argparse,json
from drama_plugin.config import load_config
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.character_package import CharacterPackageRef
from .repository import CharacterRepository

def main():
    p=argparse.ArgumentParser();p.add_argument('ref');p.add_argument('version');p.add_argument('--root',default=None);p.add_argument('--route');p.add_argument('--checksum')
    a=p.parse_args();r=CharacterRepository(a.root if a.root is not None else load_config().character_repository_root)
    package=r.load_character_package(a.ref,a.version,checksum=a.checksum)
    ref=CharacterPackageRef(character_package_ref=a.ref,character_package_version=a.version,checksum=package.manifest.checksum)
    print(json.dumps(r.resolve_character_package(ref,consumer='character-external-driver',route=a.route),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
