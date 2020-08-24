$name   = 'femm'
$url = 'http://www.femm.info/wiki/Files/files.xml?action=download&file=femm42bin_win32_21Apr2019.exe'
$url64 = 'http://www.femm.info/wiki/Files/files.xml?action=download&file=femm42bin_x64_21Apr2019.exe'
$silent = '/quiet'

Install-ChocolateyPackage $name 'exe' $silent $url $url64