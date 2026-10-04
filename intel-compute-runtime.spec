%global neo_major 26
%global neo_minor 35
%global neo_build 39758
%global neo_hotfix 11

%global _disable_lto 1
%global optflags %(echo %{optflags} | sed -e 's/ -flto//g; s/ -g3//g; s/ -gdwarf-4//g') -g0

Name:		intel-compute-runtime
Version:	%{neo_major}.%{neo_minor}.%{neo_build}.%{neo_hotfix}
Release:	1
Summary:	Intel Graphics Compute Runtime for oneAPI Level Zero and OpenCL
Group:		System/Kernel and hardware
License:	MIT
URL:		https://github.com/intel/compute-runtime
Source0:	%{url}/archive/refs/tags/%{version}/compute-runtime-%{version}.tar.gz

BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	pkgconfig(igdgmm)
BuildRequires:	%{mklibname intel-gmmlib -d} >= 22.10.2
BuildRequires:	pkgconfig(libva)
BuildRequires:	pkgconfig(libdrm)
BuildRequires:	pkgconfig(igc-opencl) >= 2.41
BuildRequires:	pkgconfig(libnl-3.0)
BuildRequires:	pkgconfig(OpenCL)
BuildRequires:	pkgconfig(OpenCL-Headers)
BuildRequires:	opencl-headers
BuildRequires:	pkgconfig(level-zero) >= 1.32.0
BuildRequires:	pkgconfig(SPIRV-Tools)
BuildRequires:	pkgconfig(SPIRV-Headers)
BuildRequires:	pkgconfig(libudev)
BuildRequires:	pkgconfig(gl)

Requires:	intel-igc >= 2.41.9
Requires:	intel-ocloc = %{EVRD}
Requires:	intel-opencl = %{EVRD}
Requires:	intel-level-zero = %{EVRD}
Provides:	bundled(drm-uapi-helper)

%description
The Intel Graphics Compute Runtime is the open-source user-space driver
for oneAPI Level Zero and OpenCL on Intel GPUs. Install this package to
pull in the OpenCL ICD, the Level Zero GPU driver and ocloc.

%package -n intel-ocloc
Summary:	Intel GPU device-binary tool
Group:		Development/Tools
Requires:	intel-igc-libs%{?_isa} >= 2.41.9

%description -n intel-ocloc
ocloc compiles, disassembles and inspects Intel GPU device binaries
used by the compute runtime.

%package -n intel-ocloc-devel
Summary:	Development files for ocloc
Group:		Development/C++
Requires:	intel-ocloc%{?_isa} = %{EVRD}

%description -n intel-ocloc-devel
Header and link library for ocloc.

%package -n intel-opencl
Summary:	OpenCL ICD for Intel GPUs
Group:		System/Libraries
Requires:	intel-igc-libs%{?_isa} >= 2.41.9
Requires:	%{mklibname intel-gmmlib 12}%{?_isa}

%description -n intel-opencl
OpenCL implementation for Intel GPUs (libigdrcl.so).

%package -n intel-level-zero
Summary:	oneAPI Level Zero driver for Intel GPUs
Group:		System/Libraries
Requires:	intel-igc-libs%{?_isa} >= 2.41.9
Requires:	%{mklibname intel-gmmlib 12}%{?_isa}
Provides:	intel-level-zero-gpu = %{EVRD}
Provides:	intel-level-zero-gpu%{?_isa} = %{EVRD}

%description -n intel-level-zero
Level Zero driver library for Intel GPUs (libze_intel_gpu).

%package -n intel-level-zero-devel
Summary:	Intel GPU Level Zero development headers
Group:		Development/C++
Requires:	intel-level-zero%{?_isa} = %{EVRD}
Requires:	%{mklibname level-zero -d}%{?_isa} >= 1.32.0

%description -n intel-level-zero-devel
Intel-specific and experimental Level Zero headers. The core ze_api.h
headers stay in the Level Zero loader development package.

%prep
%autosetup -p1 -n compute-runtime-%{version}
# Upstream adds -Werror on top of -Wall. Clang 23 warns in code gcc accepts.
sed -i 's/ -Wall -Wextra -Werror/ -Wall -Wextra/' CMakeLists.txt

%build
export CMAKE_GENERATOR=Ninja
# NEO declares clGetKernelSuggestedLocalWorkSize itself. Cooker OpenCL
# headers (2025.07.22) define the suffix macros only through 3.0.
export CFLAGS="%{optflags} -DCL_API_SUFFIX__VERSION_3_1=CL_API_SUFFIX_COMMON"
export CXXFLAGS="%{optflags} -DCL_API_SUFFIX__VERSION_3_1=CL_API_SUFFIX_COMMON"
# Mitigations belong in the kernel. NEO's userspace copies cost up to ~20%%.
%cmake \
	-DCMAKE_BUILD_TYPE=Release \
	-DNEO_OCL_VERSION_MAJOR=%{neo_major} \
	-DNEO_OCL_VERSION_MINOR=%{neo_minor} \
	-DNEO_VERSION_BUILD=%{neo_build} \
	-DNEO_VERSION_HOTFIX=%{neo_hotfix} \
	-DSKIP_UNIT_TESTS=1 \
	-DKHRONOS_GL_HEADERS_DIR="%{_includedir}/GL/" \
	-DKHRONOS_HEADERS_DIR="%{_includedir}/CL/" \
	-DKHRONOS_SPIRV_HEADERS_DIR="%{_includedir}/spirv/" \
	-DNEO_ENABLE_I915_PRELIM_DETECTION=TRUE \
	-DNEO_ENABLE_XE_PRELIM_DETECTION=TRUE \
	-DNEO_DISABLE_MITIGATIONS=TRUE \
	-DCMAKE_COMPILE_WARNING_AS_ERROR:BOOL=OFF
ninja -v

%install
DESTDIR=%{buildroot} ninja -C build install

# One ocloc is enough; the versioned binary is what NEO installs.
if ls %{buildroot}%{_bindir}/ocloc-* >/dev/null 2>&1; then
	_ocloc=$(basename $(ls -1 %{buildroot}%{_bindir}/ocloc-* | head -n1))
	ln -sf "${_ocloc}" %{buildroot}%{_bindir}/ocloc
fi

# Core Level Zero headers belong to the loader, not this driver.
for h in ze_api.h ze_ddi.h ze_ddi_common.h zes_api.h zes_ddi.h zet_api.h zet_ddi.h zer_api.h zer_ddi.h; do
	rm -f %{buildroot}%{_includedir}/level_zero/$h
done
rm -rf %{buildroot}%{_includedir}/level_zero/layers \
	%{buildroot}%{_includedir}/level_zero/loader

%files
%license LICENSE.md

%files -n intel-opencl
%license LICENSE.md
%dir %{_libdir}/intel-opencl/
%{_libdir}/intel-opencl/libigdrcl.so
%{_sysconfdir}/OpenCL/vendors/intel.icd

%files -n intel-level-zero
%license LICENSE.md
%{_libdir}/libze_intel_gpu.so.*

%files -n intel-level-zero-devel
%dir %{_includedir}/level_zero/
%{_includedir}/level_zero/*.h
%dir %{_includedir}/level_zero/driver_experimental/
%{_includedir}/level_zero/driver_experimental/*.h

%files -n intel-ocloc
%license LICENSE.md
%{_bindir}/ocloc
%{_bindir}/ocloc-*
%{_libdir}/libocloc.so

%files -n intel-ocloc-devel
%{_includedir}/ocloc_api.h
