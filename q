Help on PkgResourcesAssetDescriptor in module pyramid.path object:

class PPkkggRReessoouurrcceessAAsssseettDDeessccrriippttoorr(builtins.object)
 |  PkgResourcesAssetDescriptor(pkg_name, path)
 |  
 |  Methods defined here:
 |  
 |  ____iinniitt____(self, pkg_name, path)
 |      Initialize self.  See help(type(self)) for accurate signature.
 |  
 |  ____pprroovviiddeeddBByy____ = directlyProvides(PkgResourcesAssetDescriptor)
 |  ____pprroovviiddeess____ = directlyProvides(PkgResourcesAssetDescriptor)
 |  aabbssppaatthh(self)
 |  
 |  aabbssssppeecc(self)
 |  
 |  eexxiissttss(self)
 |  
 |  iissddiirr(self)
 |  
 |  lliissttddiirr(self)
 |  
 |  ssttrreeaamm(self)
 |  
 |  ----------------------------------------------------------------------
 |  Data descriptors defined here:
 |  
 |  ____ddiicctt____
 |      dictionary for instance variables (if defined)
 |  
 |  ____wweeaakkrreeff____
 |      list of weak references to the object (if defined)
 |  
 |  ----------------------------------------------------------------------
 |  Data and other attributes defined here:
 |  
 |  ____iimmpplleemmeenntteedd____ = classImplements(PkgResourcesAssetDescriptor, IAssetD...
 |  
 |  ppkkgg__rreessoouurrcceess = <module 'pkg_resources' from '/home/michaellauna...hon...
 |      Package resource API
 |      --------------------
 |      
 |      A resource is a logical file contained within a package, or a logical
 |      subdirectory thereof.  The package resource API expects resource names
 |      to have their path parts separated with ``/``, *not* whatever the local
 |      path separator is.  Do not use os.path operations to manipulate resource
 |      names being passed into the API.
 |      
 |      The package resource API is designed to work with normal filesystem packages,
 |      .egg files, and unpacked .egg files.  It can also work in a limited way with
 |      .zip files and with custom PEP 302 loaders that support the ``get_data()``
 |      method.
 |      
 |      This module is deprecated. Users are directed to :mod:`importlib.resources`,
 |      :mod:`importlib.metadata` and :pypi:`packaging` instead.
