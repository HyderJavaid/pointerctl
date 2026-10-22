# UNTESTED recipe (no RPM tooling on the author's machine). Build with: rpmbuild -ba packaging/rpm/pointerctl.spec
Name:           pointerctl
Version:        0.1.0
Release:        1%{?dist}
Summary:        Unofficial settings tool for mice
License:        MIT
URL:            https://github.com/naOomeow/pointerctl
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel python3-setuptools
Requires:       python3 python3-gobject gtk4 libadwaita

%description
Change DPI levels, polling rate, button functions (including keyboard shortcuts and media keys) and lighting
on a supported mouse without the manufacturer's Windows software. Currently supports the GM21.
Not affiliated with any manufacturer.

%prep
%autosetup

%build
%py3_build

%install
%py3_install
install -Dm644 packaging/data/io.github.naoomeow.Pointerctl.desktop %{buildroot}%{_datadir}/applications/io.github.naoomeow.Pointerctl.desktop
install -Dm644 packaging/data/io.github.naoomeow.Pointerctl.metainfo.xml %{buildroot}%{_datadir}/metainfo/io.github.naoomeow.Pointerctl.metainfo.xml
install -Dm644 packaging/data/io.github.naoomeow.Pointerctl.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.naoomeow.Pointerctl.svg
install -Dm644 udev/70-pointerctl.rules %{buildroot}%{_prefix}/lib/udev/rules.d/70-pointerctl.rules

%post
udevadm control --reload >/dev/null 2>&1 || :
udevadm trigger --action=change --subsystem-match=hidraw >/dev/null 2>&1 || :

%files
%license LICENSE
%doc README.md
%{_bindir}/pointerctl
%{_bindir}/pointerctl-gui
%{python3_sitelib}/pointerctl
%{python3_sitelib}/pointerctl-*.egg-info
%{_datadir}/applications/io.github.naoomeow.Pointerctl.desktop
%{_datadir}/metainfo/io.github.naoomeow.Pointerctl.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.naoomeow.Pointerctl.svg
%{_prefix}/lib/udev/rules.d/70-pointerctl.rules
