"""
ICRP 110 슬라이스별 .g4dat → ParaView VTI 변환 스크립트
사용법: python slices_to_vti.py <슬라이스_폴더> [출력파일.vti]
예시:   python slices_to_vti.py AM phantom.vti
"""

import numpy as np
import os, sys, glob

# ICRP 110 AM 복셀 크기 (mm)
VX, VY, VZ = 2.137, 2.137, 8.0

# ICRP 110 AM 고정 크기
NX, NY = 254, 127  # columns, rows

def load_all_slices(folder):
    files = sorted(
        glob.glob(os.path.join(folder, "*.g4dat")),
        key=lambda f: int(os.path.basename(f).replace("AM_slice","").replace("AF_slice","").replace(".g4dat",""))
    )
    if not files:
        print(f"오류: {folder} 에서 .g4dat 파일을 찾을 수 없습니다.")
        sys.exit(1)

    nz = len(files)
    print(f"슬라이스 {nz}개 발견: {os.path.basename(files[0])} ~ {os.path.basename(files[-1])}")

    # data shape: (nz, NY, NX) — row major, column fastest
    data = np.zeros((nz, NY, NX), dtype=np.uint8)

    for i, fpath in enumerate(files):
        if i % 50 == 0:
            print(f"  읽는 중... {i+1}/{nz}")
        with open(fpath) as f:
            vals = np.array(f.read().split(), dtype=np.uint8)
        # 헤더 3개(nx, ny, nz) 제거
        vals = vals[3:]
        # 정확히 NX*NY 개만 사용
        vals = vals[:NX * NY]
        # reshape: row(NY) x col(NX)
        data[i] = vals.reshape((NY, NX))

    print("로드 완료!")
    return nz, data


def print_stats(data):
    unique, counts = np.unique(data, return_counts=True)
    nonzero = [(u, c) for u, c in zip(unique, counts) if u > 0]
    print(f"\n장기 인덱스 종류: {len(nonzero)}개 (0 제외)")
    for u, c in nonzero[:10]:
        print(f"  인덱스 {u:3d}: {c:8,}개")


def write_vti(nz, data, out_path):
    nx = NX
    ny = NY

    # VTK ImageData: x=column(NX), y=row(NY), z=slice(NZ)
    # flatten order: x fastest → C order on (nz, ny, nx)
    flat = data.transpose(2,1,0).flatten(order="F")

    ext = "0 " + str(nx-1) + " 0 " + str(ny-1) + " 0 " + str(nz-1)
    spacing = str(VX) + " " + str(VY) + " " + str(VZ)

    header = '<?xml version="1.0"?>\n'
    header += '<VTKFile type="ImageData" version="0.1" byte_order="LittleEndian">\n'
    header += '  <ImageData WholeExtent="' + ext + '" Origin="0 0 0" Spacing="' + spacing + '">\n'
    header += '    <Piece Extent="' + ext + '">\n'
    header += '      <CellData>\n'
    header += '        <DataArray type="UInt8" Name="OrganIndex" format="ascii">\n'

    footer  = '        </DataArray>\n'
    footer += '      </CellData>\n'
    footer += '    </Piece>\n'
    footer += '  </ImageData>\n'
    footer += '</VTKFile>\n'

    print(f"\nVTI 저장 중: {out_path}")
    with open(out_path, 'w') as f:
        f.write(header)
        for i in range(0, len(flat), 10):
            f.write("          " + " ".join(str(v) for v in flat[i:i+10]) + "\n")
        f.write(footer)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"저장 완료! {size_mb:.1f} MB")
    print("")
    print("ParaView에서 열기:")
    print("  1. File -> Open -> " + os.path.basename(out_path) + " -> Apply")
    print("  2. Filters -> Threshold -> OrganIndex 1~255 -> Apply")
    print("  3. Coloring: OrganIndex")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python slices_to_vti.py <폴더> [출력.vti]")
        sys.exit(1)

    folder   = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "phantom.vti"

    nz, data = load_all_slices(folder)
    print_stats(data)
    write_vti(nz, data, out_path)
