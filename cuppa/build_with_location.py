#          Copyright Jamie Allsop 2014-2017
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)

#-------------------------------------------------------------------------------
#   build_with_location
#-------------------------------------------------------------------------------

import os

import cuppa.location
from cuppa.log import logger
from cuppa.colourise import as_notice, as_error, as_info


class LocationDependencyException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class base(object):

    _name = None
    _cached_locations = {}
    _default_location = None
    _default_include = None
    _default_sys_include = None
    _includes = None
    _sys_includes = None
    _extra_sub_path = None
    _source_path = None
    _linktype = None
    _prebuilt_objects = {}
    _prebuilt_libraries = {}

    @classmethod
    def add_options( cls, add_option ):
        location_name       = cls._name + "-location"
        branch_name         = cls._name + "-branch"
        include_name        = cls._name + "-include"
        sys_include_name    = cls._name + "-sys-include"
        extra_sub_path_name = cls._name + "-extra-sub-path"
        source_path_name    = cls._name + "-source-path"
        linktype_name       = cls._name + "-linktype"

        add_option( '--' + location_name, dest=location_name, type='string', nargs=1, action='store',
                    help = cls._name + ' location to build against' )

        add_option( '--' + branch_name, dest=branch_name, type='string', nargs=1, action='store',
                    help = cls._name + ' branch to build against. Providing a branch is optional' )

        add_option( '--' + include_name, dest=include_name, type='string', nargs=1, action='store',
                    help = cls._name + ' include sub-directory to be added to the include path. Optional' )

        add_option( '--' + sys_include_name, dest=sys_include_name, type='string', nargs=1, action='store',
                    help = cls._name + ' include sub-directory to be added to the system include path. Optional' )

        add_option( '--' + extra_sub_path_name, dest=extra_sub_path_name, type='string', nargs=1, action='store',
                    help = cls._name + ' extra (relative) sub path to locate the dependency. Optional' )

        add_option( '--' + source_path_name, dest=source_path_name, type='string', nargs=1, action='store',
                    help = cls._name + ' path to source files. Optional' )

        add_option( '--' + linktype_name, dest=linktype_name, type='string', nargs=1, action='store',
                    help = cls._name + ' linktype: static (default) or shared. Optional' )


    @classmethod
    def add_to_env( cls, env, add_dependency  ):
        add_dependency( cls._name, cls.create )


    @classmethod
    def location_id( cls, env ):
        location = env.get_option( cls._name + "-location" )
        branch   = env.get_option( cls._name + "-branch" )

        if not location and cls._default_location:
            location = cls._default_location
        if not location and branch:
            location = env['branch_root']
        if not location and branch:
            location = env['thirdparty']
        if not location:
            logger.debug( "No location specified for dependency [{}]. Dependency not available.".format( cls._name.title() ) )
            return None

        if location:
            location = os.path.expanduser( location )

        return (location, branch)


    @classmethod
    def _get_location( cls, env ):
        location_id = cls.location_id( env )
        if not location_id:
            return None
        if location_id not in cls._cached_locations:
            location = location_id[0]
            branch = location_id[1]
            try:
                cls._cached_locations[location_id] = cuppa.location.Location( env, location, branch=branch, extra_sub_path=cls._extra_sub_path )
            except cuppa.location.LocationException as error:
                logger.error(
                        "Could not get location for [{}] at [{}] with branch [{}] and extra sub path [{}]. Failed with error [{}]"
                        .format( as_notice( cls._name.title() ), as_notice( str(location) ), as_notice( str(branch) ), as_notice( str(cls._extra_sub_path) ), as_error( error ) )
                )
                return None

        return cls._cached_locations[location_id]


    @classmethod
    def create( cls, env ):

        location = cls._get_location( env )
        if not location:
            return None

        if not cls._includes:
            include = env.get_option( cls._name + "-include" )
            cls._includes = include and [include] or []

        if not cls._sys_includes:
            sys_include = env.get_option( cls._name + "-sys-include" )
            cls._sys_includes = sys_include and [sys_include] or []

        if cls._default_include:
            cls._includes.append( cls._default_include )

        if cls._default_sys_include:
            cls._sys_includes.append( cls._default_sys_include )

        if not cls._source_path:
            cls._source_path = env.get_option( cls._name + "-source-path" )

        if not cls._linktype:
            cls._linktype = env.get_option( cls._name + "-linktype" )

        return cls( env, location, includes=cls._includes, sys_includes=cls._sys_includes, source_path=cls._source_path, linktype=cls._linktype )


    def __init__( self, env, location, includes=[], sys_includes=[], source_path=None, linktype=None ):

        self._location = location

        if not includes and not sys_includes:
            includes = [self._location.local()]

        self._includes = []
        for include in includes:
            if include:
                self._includes.append( os.path.isabs(include) and include or os.path.join( self._location.local(), include ) )

        self._sys_includes = []
        for include in sys_includes:
            if include:
                self._sys_includes.append( os.path.isabs(include) and include or os.path.join( self._location.local(), include ) )

        if source_path:
            self._source_path = os.path.isabs(source_path) and source_path or os.path.join( self._location.local(), source_path )

        if not linktype:
            self._linktype = "static"
        else:
            self._linktype = linktype


    def __call__( self, env, toolchain, variant ):
        env.AppendUnique( INCPATH = self._includes )
        env.AppendUnique( SYSINCPATH = self._sys_includes )


    @classmethod
    def lazy_create_node( cls, variant_key, cached_nodes ):
        if not cls._name in cached_nodes:
            cached_nodes[cls._name] = {}

        if not variant_key in cached_nodes[cls._name]:
            cached_nodes[cls._name][variant_key] = {}

        return cached_nodes[cls._name][variant_key]


    def build_library_from_source( self, env, sources=None, library_name=None, linktype=None ):

        if not self._source_path and not sources:
            logger.warn( "Attempting to build library when source path is None" )
            return None

        if not library_name:
            library_name = self._name

        if not linktype:
            linktype = self._linktype

        variant_key = env['tool_variant_dir']

        prebuilt_objects   = self.lazy_create_node( variant_key, self._prebuilt_objects )
        prebuilt_libraries = self.lazy_create_node( variant_key, self._prebuilt_libraries )

        local_dir = self._location.local()
        local_folder = self._location.local_folder()

        build_dir = os.path.join( env['build_root'], local_folder, env['tool_variant_working_dir'] )
        final_dir = os.path.normpath( os.path.join( build_dir, env['final_dir'] ) )

        logger.debug( "build_dir for [{}] = [{}]".format( as_info(self._name), build_dir ) )
        logger.debug( "final_dir for [{}] = [{}]".format( as_info(self._name), final_dir ) )

        obj_suffix = env['OBJSUFFIX']
        obj_builder = env.StaticObject
        lib_builder = env.BuildStaticLib

        if linktype == "shared":
            obj_suffix = env['SHOBJSUFFIX']
            obj_builder = env.SharedObject
            lib_builder = env.BuildSharedLib

        if not sources:
            sources = env.RecursiveGlob( "*.cpp", start=self._source_path, exclude_dirs=[ env['build_dir'] ] )

        objects = []
        for source in sources:
            rel_path = os.path.relpath( str(source), local_dir )
            rel_obj_path = os.path.splitext( rel_path )[0] + obj_suffix
            obj_path = os.path.join( build_dir, rel_obj_path )
            if not rel_obj_path in prebuilt_objects:
                prebuilt_objects[rel_obj_path] = obj_builder( obj_path, source )
            objects.append( prebuilt_objects[rel_obj_path] )

        if not linktype in prebuilt_libraries:
            library = lib_builder( library_name, objects, final_dir = final_dir )
            if linktype == "shared":
                library = env.Install( env['abs_final_dir'], library )
            prebuilt_libraries[linktype] = library
        else:
            logger.trace( "using existing library = [{}]".format( str(prebuilt_libraries[linktype]) ) )

        return prebuilt_libraries[linktype]


    def local_sub_path( self, *paths ):
        return os.path.join( self._location.local(), *paths )


    @classmethod
    def name( cls ):
        return cls._name

    def version( self ):
        return str(self._location.version())

    def repository( self ):
        return self._location.repository()

    def branch( self ):
        return self._location.branch()

    def revisions( self ):
        return self._location.revisions()



class LibraryMethod(object):

    def __init__( self, location_dependency, update_env, sources=None, library_name=None, linktype=None ):
        self._location_dependency = location_dependency
        self._update_env = update_env
        self._sources = sources
        self._library_name = library_name
        self._linktype = linktype


    def __call__( self, env ):
        self._update_env( env )
        return self._location_dependency.build_library_from_source( env, self._sources, self._library_name, self._linktype )



def location_dependency( name, location=None, include=None, sys_include=None, extra_sub_path=None, source_path=None, linktype=None ):
    return type(
            'BuildWith' + name.title(),
            ( base, ),
            {   '_name': name,
                '_default_location': location,
                '_default_include': include,
                '_default_sys_include': sys_include,
                '_extra_sub_path': extra_sub_path,
                '_source_path': source_path,
                '_linktype': linktype
            }
    )



