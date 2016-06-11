#/bin/sh
# Script to install dependencies that are not available through pip
# Stop on any errors
set -e

# Extract and install everything in the home directory so that the paths match
# with those in .travis.yml
pushd $HOME

# LIRC
if [ ! "$(ls -A lirc_install)" ]; then
    git clone git://git.code.sf.net/p/lirc/git lirc
    pushd lirc
    ./autogen.sh
    ./configure --prefix=$HOME/lirc_install CFLAGS='-g -O2 -lrt' CXXFLAGS='-g -O2 -lrt'
    make systemdsystemunitdir=$HOME/lirc_systemd
    make install systemdsystemunitdir=$HOME/lirc_systemd
    popd
fi

if [ ! "$(ls -A qt_install)" ]; then
    # SIP
    wget http://sourceforge.net/projects/pyqt/files/sip/sip-4.18/sip-4.18.tar.gz
    tar xzf sip-4.18.tar.gz
    pushd sip-4.18
    python configure.py -b $HOME/qt_install/bin -d $HOME/qt_install/lib/python2.7/site-packages -e $HOME/qt_install/include --sipdir $HOME/qt_install/share/sip
    make
    make install
    popd

    # PyQt4
    wget http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz
    tar xzf PyQt-x11-gpl-4.11.4.tar.gz --keep-newer-files
    pushd PyQt-x11-gpl-4.11.4
    python configure.py -c --confirm-license --no-designer-plugin -e QtCore -e QtGui -d $HOME/qt_install/lib/python2.7/site-packages --sipdir $HOME/qt_install/share/sip
    make
    make install
    popd
fi

popd
