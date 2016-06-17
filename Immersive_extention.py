#filename        : Tangible landscape Immersive Extension (EETLM)
#description     :This script takes various forms of geo-coordinated data and visualize them in 3D mode using blender (v 2.76) open source game-engine.
#                 Data and coordinates are imported using GIS add-on. Using the built-in modal timer operator module,
#                 the script dynamically conforms to the incoming data generated by tangible landscapes.
#author          :Payam Tabrizian
#date            :4.22.2016
#version         :.1
#usage           :Blender v(2.77a)
#notes           :
#python_version  :3.2 
#==============================================================================

import bpy
import os
import math
import datetime
import bmesh
from bpy.props import *
import shutil

##### default values for Global variables  ######
# watchFolder--folder for incoming files from GRASS GIS
# scratchPath-- folder for writing scratch files
# pointPath -- PointCloud file (.ply )
# camPath -- Camera coordinates file (.txt) : generatad by GRASS as user locates it on the kinetic model with laser pointer. 
# orthoPath -- path and name of the orthophoto (.png)
# DEMPath -- Digital Elevation Model:  generatad by GRASS as user reshapes the kinetik sand (.tiff)
# plane -- a plane that represents the terrain surface and dynamicly conforms to the reshaped landscape   
# xtransfer , Y trasnfer -- GEO coordinates of the GIS model as defined by GRASS.
                           #this defines the coordinates using which all the incoming data can be adjusted to blender model
# Ztranslate : Z correction to correct exaggeration level of the input GRASS

watchName="Watch"
textureFile="texture.png"
scratchFolder="scratch"
pointFile= "point.ply"
cameraFile="camCoord.txt"
planeFile="plane.tif"
DEMFile="elev.tif"
orthoFile= "ortho.tif"
treePatchFile="treepatch_2.shp"
lineFile="line.shp"
vantageFile="vantage.shp"
waterFile="water.shp"
# the following parameters denote the Latitude , longitude of the center of the main geometry # 
xtransfer= 638650   
ytransfer= 220407
Ztranslate=0

########-----------------------###########.

watchFolder= os.path.dirname(bpy.path.abspath("//"))+"/"+ watchName
scratchPath= os.path.dirname(bpy.path.abspath("//"))+"/"+ scratchFolder
pointPath= os.path.join(watchFolder,pointFile)
planePath=bpy.path.abspath("//")+"/"+planeFile
camPath= os.path.join(watchFolder,cameraFile)
DEMPath= os.path.join(watchFolder,DEMFile)
texturePath= os.path.join(watchFolder,textureFile)
orthoPath= os.path.join(watchFolder,orthoFile)
patchPath= os.path.join(watchFolder,treePatchFile)
linePath= os.path.join(watchFolder,lineFile)
vantagePath=os.path.join(watchFolder,vantageFile)
waterPath= os.path.join(watchFolder,waterFile)
planeShow= True
plane=planeFile.split(".")[0]

class initSetup(bpy.types.Operator):
    
    """ Clears the scene and creates the essential objects and parameters """
    " The integer values (light inensity , subdivision values and etc. ) are the essentail values for the setup in any geoSpatial ENV. " 
    
    bl_idname = "wm.initilialize_scene_parameters"
    bl_label = "Initialize Scene"

    # Define blender scene extent# 
    bpy.data.scenes["Scene"]["Georef X"]=xtransfer
    bpy.data.scenes["Scene"]["Georef Y"]=ytransfer
    # animation properties # 
    bpy.context.scene.render.fps = 5
    bpy.context.scene.frame_end = 100  

    def execute(self,context):       
        scene = bpy.context.scene
        # Clears the current scene# 
        for ob in scene.objects:
            ob.hide=False
            ob.select=True
            bpy.ops.object.delete()

        # imports and subdivides the surface plane#    
        bpy.ops.importgis.georaster(filepath=planePath,importMode="PLANE")
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='EDIT')
            obj = bpy.context.active_object       
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            face=bm.faces[0]
            face.select=True
            bpy.ops.mesh.subdivide(number_cuts=1000, smoothness=0.5)
            bmesh.update_edit_mesh(obj.data, True)
            bpy.ops.object.mode_set(mode='OBJECT')
        
        #Add sun#  
        bpy.ops.object.add(type="LAMP", location=(0,0,500))
        bpy.context.object.data.type = 'SUN'
        bpy.context.object.data.sky.use_sky = True
        bpy.context.object.data.shadow_method = 'RAY_SHADOW'
        
        # Creates the Human_view_camera#
        bpy.ops.object.add(type="CAMERA", location=(0,0,0))
        bpy.ops.transform.rotate(value=-4.7, axis=(1, 0, 0), constraint_axis=(True,False,False))
        bpy.context.object.data.clip_end = 1000
        bpy.context.object.data.clip_start = 0
        bpy.context.object.data.lens = 25
        bpy.context.object.data.sensor_width = 40
        humanCamera=bpy.data.objects["Camera"]
         
        #Creates the birdview_cam and a bezier circle for the camera orbit# 

        bpy.ops.curve.primitive_bezier_circle_add(radius=400,location=(0,0,300))
        Circle=bpy.data.objects["BezierCircle"]
        Circle.select=False
        bpy.ops.object.add(type="CAMERA", location=(-1,-400,300))
        bpy.context.object.rotation_euler[0] = 0.70
        bpy.context.object.data.clip_end = 1000
        bpy.context.object.data.clip_start = 0
        bpy.context.object.data.lens = 25
        bpy.context.object.data.sensor_width = 60
        birdCamera=bpy.data.objects["Camera.001"]

        #selectOnly("Camera.001")
        Circle.select=True
        bpy.context.scene.objects.active = Circle
        bpy.ops.object.parent_set(type="FOLLOW")
        Circle.hide=True
        cameraView("Camera.001")              
        return {"FINISHED"}

def importObject(input,type, filePath=None):
        
    """Imports multiple type of objects , meshes and textfiles contents
    Keyword arguments. Checks for and Removes existing instances of the passed object.
    
    Keyword arguments:               
    input  -- Object instance name to be replaced
    type   -- 1. Camera coordinates (comma seperated x, y, z) returns a list of x,y
              2. Stanford Pointcloud (.ply) file , input is the path
              3. Shapefile , uses the ArcGis addon. Sample inputs can be trees, camera path buildings or any Arcgis vecore shapefiles            
    filePath -- location of the imported file
    delExisting-- Check if the object instance exists and delete it  
    """

    if type== "pointcloud":
        
        try:       
            bpy.ops.import_mesh.ply(filepath=input)
            bpy.ops.object.origin_set(type="GEOMETRY_ORIGIN")
            print ("file {0} successfully imported at {1}".format(input, getTime("time")))
            
        except:
           
            raise NameError("Cannot import [0]".format(input))

    elif type== "Camera":

        try:
            camText = open(input,"r")
            coord = camText.read().split(",")
            x=int(coord[0])
            y=int(coord[1])
            z=float(coord[2])
            camText.close()
            print ("Camerafile {0} successfully imported at {1}".format(input, getTime("time")))
            return [x,y]

        except:

            raise NameError("Cannot import {0}".format(input))
        
    elif type== "ShapeFile":
        bpy.ops.import_mesh.ply(filepath=pointPath,directory=os.path.dirname(pointPath),filter_glob="*.ply")

    # open camera textfile and returns the x and y coordinates " 
    elif type== "Camera":                                 
        camText = open(camPath,"r")
        coord = camText.read().split(",")
        x=int(coord[0])
        y=int(coord[1])
        z=float(coord[2])
        camText.close()
        return [x,y]
    
    #elif type== "treePatch":
        #bpy.ops.importgis.shapefile(filepath=input,filter_glob="*.shp")
        #print ("imported")
        
           
def shrinkRaster2Obj(raster,target,method= "NEAREST_VERTEX",zTranslate= -20, delModifier= True):
        
    """allows an object to shrink to the surface of another object.
    It moves each vertex of the object being modified to the closest position on the surface of the given mesh
    
    Keyword arguments:
    raster -- is the
    target --
    method -- uses one of the three shrinkwrap methods.(default NEAREST_VERTEX)
    ztranslate -- justifies the produced mesh on the target. It is particulalry usefull for pointclouds.(default 0)
    delModifier -- defines whether the previous modifiers shoyuld be deleted or not. 
    """

    try:
        rasterObj= bpy.data.objects[raster]
        target= bpy.data.objects[target]

    except:
        
        raise NameError("Shrinkwrap Unsuccessfull: Either the raster or target object does not exist")
    

    # select only the plane delete all previous modifiers #
    selectOnly(raster)
    bpy.context.scene.objects.active = rasterObj  
    if delModifier:
        rasterObj.modifiers.clear()
        
    bpy.ops.transform.translate(value=(0, 0, -Ztranslate), constraint_axis=(False, False, True),
                                constraint_orientation="GLOBAL", mirror=False, proportional='DISABLED',
                                proportional_edit_falloff='SMOOTH', proportional_size=1, release_confirm=True)
    # apply shrinkwrap Modifier #
    bpy.ops.object.modifier_add(type='SHRINKWRAP')
    bpy.context.object.modifiers['Shrinkwrap'].target=target
    bpy.context.object.modifiers["Shrinkwrap"].wrap_method = 'NEAREST_VERTEX'
    
               
def smooth(obj,factor=2,iterations=4,zTranslate=0) :

    """Smooths a mesh by flattening the angles between adjacent faces in it.
    It smooths without subdividing the mesh - the number of vertices remains the same.

    Keyword arguments:
    obj -- name of the object
    factor -- The factor to control the smoothing amount. Higher values will increase the effect.
    iterations -- number of smoothing iterations, equivalent to executing the smooth tool multiple times.
    """
    selectOnly(obj)
    bpy.ops.object.modifier_add(type="SMOOTH")
    bpy.data.objects[obj].modifiers["Smooth"].factor=factor
    bpy.data.objects[obj].modifiers["Smooth"].iterations=iterations
    bpy.ops.transform.translate(value=(0, 0, zTranslate), constraint_axis=(False, False, True),
                                constraint_orientation="GLOBAL", mirror=False, proportional="DISABLED",
                                proportional_edit_falloff="SMOOTH", proportional_size=1, release_confirm=True)

     
def changeTex(obj,texturePath):

    """Changes the texture of the plane based on the passed texturePath
    To maximize performance texture swap is done changing surface material instead of importing a new raster object"""
       
    obj= selectOnly(obj)
    texPath = os.path.expanduser(texturePath)
    # remove previous material from material slot #
    if obj.material_slots:
       # for slot,index in zip(obj.material_slots, range(20)):
        for slot in obj.material_slots:
            bpy.ops.object.material_slot_remove() 

    try:
        print (texPath)
        img = bpy.data.images.load(texPath)
        
    except:
        raise NameError("Cannot load image [0]".format(texPath))
 
    # Create image texture from image  
    cTex = bpy.data.textures.new("Raster Tec", type = "IMAGE")
    cTex.image = img
    # Create material
    mat = bpy.data.materials.new('P')
    # Add texture slot for color texture
    mtex = mat.texture_slots.add()
    mtex.texture = cTex
    mtex.texture_coords = 'UV'
    mtex.use_map_color_diffuse = True 
    mtex.use_map_color_emission = True 
    mtex.emission_color_factor = 0.5
    mtex.use_map_density = True 
    mtex.mapping = 'FLAT'       
    me = obj.data
    me.materials.append(mat)
        
def selectOnly(obj, delete= False):
    
    """ unselects all objects and selects the passed object"""
    
    if bpy.data.objects.get(obj):
        obj=bpy.data.objects[obj]
        for ob in bpy.context.scene.objects:
            ob.select=False        
        obj.select=True       
        if delete:
            bpy.ops.object.delete()
    return obj
      
def translateLoc(obj,pos,HumanHeight=+1.8):
    
    """ moves the passed object and returns the new location """    

    obj= bpy.data.objects[obj]
    obj.location=[pos[0],pos[1],pos[2]+HumanHeight]
    return obj.location

def getVertexList(obj,precision=0):
    
    """ returns a dictionary with all the object vertices as keys and
    a list of coordinaltes as walues """
    
    obj= bpy.data.objects[obj]
    objData=obj.data
    vertDic={}
    #Looks into the object vertices ##
    for vert in objData.vertices:
        vertX= int((round(vert.co.x,precision)))
        vertY= int((round(vert.co.y,precision)))
        vertZ= int((round(vert.co.z,precision)))
        vertDic[vert.index]=[vertX,vertY,vertZ]
    return vertDic

def findNearVert(coord,targetDic,estimate=2.5):
    
    """ gets a list of x and y along with a dictionary of object vertices and returns
    the nearest vertex index from the target object dictionary
    estimate --defines 

    """
    x1= int(coord[0]-xtransfer)
    y1= int(coord[1]-ytransfer)
    print (x1,y1)
    distList=[]
    distDic={}
    xList=[]
    
    for vertex in targetDic:       
        x2= targetDic[vertex][0]
        y2= targetDic[vertex][1]        
        # calulates the distance between the object vertices #
        dist=round(math.sqrt(((x2-x1)**2)+((y2-y1)**2)),1)                        
        if dist < estimate:
            distList.append(dist)
            distDic[dist]=targetDic[vertex]           
    if distDic: 
            nearestVert=(distDic[min(distDic)])
            print ("Nearest vertex found has distance of {0} meters and coordinates of {1}:".format( min(distDic),distDic[min(distDic)]))    
            return nearestVert        
    else:
            return 

def cameraView(camera):
    
        """ gets a camera name and conforms the view point accordingly"""
        selectOnly(camera)
        cameraObj=bpy.data.objects[camera]
        bpy.context.scene.objects.active = cameraObj
        bpy.ops.view3d.object_as_camera()       

def getTime(returnType):
    
    """ Rerturns diffrent outputs for time as required in diffrent functions """
    
    current_time = str(datetime.datetime.now().time())
    seconds= current_time.split(":")[2][:2]
    min= current_time.split(":")[1]
    fullTime=current_time.replace(":","")[:6]
    if returnType=="min":
        return min
    elif returnType== "sec":
        return seconds
    elif returnType== "time":
        return fullTime

def makeScratchfile(oldfile,newfile,ext):
    
    """ Renames the passed file relative to the current time and puts in the scratch path,  """
 
    try:
        
        out_time=getTime("time")
        outputpath= newfile+"/"+ scratchFolder + out_time +ext
        os.rename(oldfile,outputpath)
        print ("file {0} successfully saved and renamed as {1} ".format(oldfile,outputpath))
        return outputpath
    
    except:
        raise NameError("could not rename the {0} file ".format(oldfile))


def particle(obj):
    
    """ draw patch of tees using particle system modifier"""
    
    patch=bpy.data.objects[obj]
    bpy.ops.object.particle_system_add()
    psys1 = patch.particle_systems[-1]
    #psys1.name="tree"
    pset1 = psys1.settings
    pset1.name = 'TreePatch'
    pset1.type = 'HAIR'
    pset1.use_rotation_dupli=False
    print ("1")
    pset1.use_dead=True
    pset1.render_type='OBJECT'
    pset1.dupli_object = bpy.data.objects["tree.003"]
    #pset1.frame_start = 1
    #pset1.frame_end = 1
    #pset1.lifetime = 50
    print ("2")
    pset1.lifetime_random = 0.0
    pset1.emit_from = 'FACE'
    pset1.count=300
    pset1.use_render_emitter = True
    #pset1.object_align_factor = (0,0,1)
    print ("3")
    pset1.use_emit_random=True
    pset1.userjit=70
    pset1.use_modifier_stack=True
    pset1.hair_length=3.5
    
    pset1.use_rotations=True

    pset1.use_rotation_dupli=True
    pset1.particle_size=1
    pset1.size_random=.7
    pset1.rotation_mode='OB_Y'
  

def changeMat(obj,mat):  
    obj=bpy.data.objects[obj]
    #selectOnly(obj)
    mat = bpy.data.materials.get(mat)

    if obj.data.materials:
        # assign to 1st material slot
        obj.data.materials[0] = mat
    else:
        # no slots
        obj.data.materials.append(mat)


def removeMore(index):
   oblist= bpy.data.objects
   for obj in oblist :
       if obj.name.startswith(index):
           #selectOnly(obj,delete=True)
           obj.select=True
           bpy.ops.object.delete()   

           
def subdivide(cutNo):
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='EDIT')
        obj = bpy.context.active_object       
        bm = bmesh.from_edit_mesh(obj.data)
        bpy.ops.mesh.subdivide(number_cuts=cutNo, smoothness=0.2)
        bmesh.update_edit_mesh(obj.data, True)
        bpy.ops.object.mode_set(mode='OBJECT')

    

class adapt:
    
    """ Adpats the scene objects to the incoming vector , raster and empty files """
    
    def __init__(self,signal=None):
        
        # Scene objects#
        
        self.signal = signal
        self.pointCloud=pointFile.split(".")[0]
        self.plane="plane"
        self.treePatch= "TreePatch"
        self.plane= plane
        self.pathLine="line"
        self.point= pointFile.split(".")[0]
        self.indexlist=[]
        self.importedlist=[]
        self.pointlist=[]
        self.texture="texture.tif"
        self.humanCamera="Camera"
        self.humanTarg="HumanCamTarg"
        self.vantage="vantage"
        self.target="camtarget"
        self.vantageCam="VantageCam"
        
        
    def terrain(self):
        
        try:
            
            importObject(pointPath,"pointcloud")

            if bpy.data.objects.get(self.pointCloud+".001"):
               bpy.data.objects[self.point].hide=False
               bpy.data.objects[self.point].hide=False
               selectOnly(self.pointCloud,delete=True)
               obj=bpy.data.objects[self.pointCloud+".001"]
               obj.name=self.pointCloud
                
            shrinkRaster2Obj(self.plane,self.pointCloud) 
            smooth(self.plane)
            #bpy.ops.analysis.nodes()
            
            # Shrinks the existing tree patch layer to the plane#
            
            if bpy.data.objects[self.treePatch].hide: 
                treeHide=True
                bpy.data.objects[self.treePatch].hide=False                 
            else:
                treeHide=False
    
           # shrinkRaster2Obj(self.treePatch,self.point,delModifier=False)

            if treeHide:
                bpy.data.objects[self.treePatch].hide=True
            bpy.data.objects[self.treePatch].select=False    
            # saves the blender file and saves the old pointfile#
            # bpy.ops.wm.save_mainfile()
            print ("blender file {0} saved ".format(bpy.path.basename(bpy.context.blend_data.filepath)))
            makeScratchfile(pointPath,scratchPath,"_point.ply")

            # Checks for the current state of the plane show and manages the visivility of the relevant objects.
            if planeShow:
                bpy.data.objects[self.point].hide=True 
                                     
            else:
                bpy.data.objects[self.plane].hide=True
                selectOnly(self.point,delete=False)
            return "finished"
        except:
            print ("not done")
 
    def textureM(self): 
 
        try:
            selectOnly(self.plane)
            tex=makeScratchfile(texturePath,scratchPath,"_tex.png") 
            changeTex(self.plane,tex) 
            return "finished"
        except:
            print ("cannot change texture")
            
    
    def vantagePoint(self):

        if bpy.data.objects.get(self.vantage):
           selectOnly(self.vantage,delete=True)
        
        try:
            bpy.ops.importgis.shapefile(filepath=vantagePath)

            van=bpy.data.objects[self.vantage]
            cam=bpy.data.objects[self.vantageCam]
            tar=bpy.data.objects[self.target]
            #subdivide(0)

            shrinkRaster2Obj(self.vantage,self.plane,delModifier=False)
           
            me = van.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings='PREVIEW')
            me.transform(van.matrix_world)
            cam.location=[me.vertices[0].co.x,me.vertices[0].co.y,me.vertices[0].co.z+1.8]
            tar.location=[me.vertices[-1].co.x,me.vertices[-1].co.y,me.vertices[0].co.z+6]

            makeScratchfile(vantagePath,scratchPath,"_van.shp")
            makeScratchfile(os.path.join(watchFolder,vantagePath[:-4]+".dbf") ,scratchPath,"_line.dbf")
            makeScratchfile(os.path.join(watchFolder,vantagePath[:-4]+".prj") ,scratchPath,"_line.prj")
            makeScratchfile(os.path.join(watchFolder,vantagePath[:-4]+".shx") ,scratchPath,"_line.shx")
            cameraView(self.vantageCam)
        except:
            print ("vantage not imported")
            
    def trail(self) : 
        
        print ("entering trail Mode")
        
        if bpy.data.objects.get(self.pathLine):
         selectOnly(self.pathLine,delete=True)

        try:
            bpy.ops.importgis.shapefile(filepath=linePath)
            makeScratchfile(os.path.join(watchFolder,linePath) ,scratchPath,"_line.shp")
            makeScratchfile(os.path.join(watchFolder,linePath[:-4]+".dbf") ,scratchPath,"_line.dbf")
            makeScratchfile(os.path.join(watchFolder,linePath[:-4]+".prj") ,scratchPath,"_line.prj")
            makeScratchfile(os.path.join(watchFolder,linePath[:-4]+".shx") ,scratchPath,"_line.shx")
            
            line=bpy.data.objects[self.pathLine]
            subdivide(0)
            obj=bpy.context.scene.objects.active.name   
            shrinkRaster2Obj(obj,self.plane,delModifier=False)

            me = line.to_mesh(scene=bpy.context.scene, apply_modifiers=True, settings='PREVIEW')
            me.transform(line.matrix_world)     
            cam=bpy.data.objects[self.humanCamera]        
            cam.location=[me.vertices[0].co.x,me.vertices[0].co.y,me.vertices[0].co.z+1.8]  
            bpy.ops.object.convert(target='CURVE')      
            selectOnly(self.humanCamera,delete=False)
            line.select=True
            bpy.ops.object.parent_set(type='FOLLOW')
            
        except:
            print ("Camera trajectory import unsucsessfull")               
        
        
    def treePatchFill(self,patchpath):
        
           if patchpath=="empty" :                  
                removeMore("treep")
                makeScratchfile(os.path.join(watchFolder,"empty.txt") ,scratchPath, "_empty.txt")
                "print Tree patches cleared"  
                      
           else:  
                time=getTime("sec")
                         
                try:
                    bpy.ops.importgis.shapefile(filepath=patchpath)                    
                    obj=bpy.context.scene.objects.active.name
                    shrinkRaster2Obj(obj,"plane",delModifier=False)
                    obj=bpy.context.scene.objects.active.name
                    changeMat(obj,"Transparent")
                    particle(obj)
                    return "imported"
            
                except:
                   print ("tree patch drawing failed")
         
    def waterFill(self, waterType=None):
        
        
        
           try:
                
                #if bpy.data.objects.get("water"):
                    #selectOnly("water",delete=True)
            
                bpy.ops.importgis.shapefile(filepath=waterPath)
                
                if bpy.data.objects.get("water"+".001"):
                    bpy.data.objects["water"].hide=False
                    bpy.data.objects["water"].hide=False
                    selectOnly("water",delete=True)
                    obj=bpy.data.objects["water"+".001"]
                    obj.name="water"
            

                obj=bpy.context.scene.objects.active.name
                shrinkRaster2Obj(obj,"plane",delModifier=False)
                smooth ("water", .7)
                changeMat("water","Water")
                makeScratchfile(waterPath ,scratchPath, "_water.shp")
                makeScratchfile(os.path.join(watchFolder,waterPath[:-4]+".dbf") ,scratchPath,"_water.dbf")
                makeScratchfile(os.path.join(watchFolder,waterPath[:-4]+".prj") ,scratchPath,"_water.prj")
                makeScratchfile(os.path.join(watchFolder,waterPath[:-4]+".shx") ,scratchPath,"_water.shx")
                
                return "imported"
            
           except:
               print ("water patch drawing failed")
               
                          
 
class ModalTimerOperator(bpy.types.Operator):
    
        """Operator which interatively runs from a timer"""

        bl_idname = "wm.file_listener"
        bl_label = "Modal Timer Operator"
        _timer = 3

        def modal(self, context, event):      
            if event.type in {"RIGHTMOUSE", "ESC"}:
                return {"CANCELLED"}
            
            
            # this condition encomasses all the actions required for watching the folder and related file/object operations .
            if event.type == "TIMER":
                
                a= getTime('sec')

                if int(a)%2==0:
                    
                    #Make a list of file in watchFolder#
                    tempFolder= os.path.dirname(bpy.path.abspath("//"))+"/"+ "temp"
                    fileList=(os.listdir(watchFolder))
                    selectedfiles= {}
                    
                    ## check for replacable single instance objects ### 
                     
                    # check for point cloud#
                    if pointFile in fileList : 

                        try:
                            adapt().terrain()
                            self.adaptMode="point"
                                
                        except : 
                            print ("point file found but not imported") 
                            
                    # check for texture#
                    if textureFile in fileList: 
                        selectOnly(self.plane)
                        adapt().textureM()
                        self.adaptMode="texture" 
                        
                    # check for water vector#
                    if waterFile in fileList:
                        adapt().waterFill()
                       
                    # check for trail path vector#           
                    if lineFile in fileList: 
                        adapt().trail()
                        self.adaptMode="camPath" 
                        
                    # check for empty signals#   
                    if self.emptyTree in fileList: 
                        
                        adapt().treePatchFill("empty")
                        self.adaptMode="empty"              
                    # check for vantagepoints#   
                    elif vantageFile in fileList: 
                        
                        adapt().vantagePoint()
                        self.adaptMode="Vantage" 

                    ## check for Multiple Instance objects ### 

                    ## Tree patches ## 
                    newobj=None 
                        
                    for file in fileList:
                        if file.startswith("treepatch_") and file[-4:]==".shp": 
                            if os.path.exists(os.path.join(watchFolder,file[:-4]+".shx")) and (os.path.join(watchFolder,file[:-4]+".dbf")) and (os.path.join(watchFolder,file[:-4]+".prj")) :
                                index=file.split("_")[1].split(".")[0]
                                if int(index) not in self.indexlist :
                                    self.indexlist.append(int(index))
                        if len(self.indexlist):
                            newobj="treepatch_"+str(max(self.indexlist))
                         
                    if newobj and not bpy.data.objects.get(newobj) and newobj not in self.importedlist:
                       patchpath=os.path.join(watchFolder,(newobj+".shp"))
                       if adapt().treePatchFill(patchpath)=="imported":
                            self.importedlist.append(newobj)            
 
            return {"PASS_THROUGH"}
                    
        def execute(self, context):
            
            wm = context.window_manager
            wm.modal_handler_add(self)  
            self._timer = wm.event_timer_add(.5, context.window)
            self.plane= plane
            self.point= pointFile.split(".")[0]
            self.treePatch= "TreePatch"
            self.indexlist=[]
            self.importedlist=[]
            self.emptyTree= "empty.txt"
            self.adaptMode=None
          
            for file in os.listdir(watchFolder):
                try:
                    os.remove(os.path.join(watchFolder,file))
                except :
                    print ("Could not remove file")        
 
            return {"RUNNING_MODAL"}

        def cancel(self, context):
           wm = context.window_manager
           wm.event_timer_remove(self._timer)

class TA_IVE(bpy.types.Operator):

    """ reinitates the scene and turn on watch-Mode"""

    bl_idname = "wm.execmain"
    bl_label = "Run_Tangible_Landscapes_IVE"
    
    def execute(self,context) :      
        bpy.ops.wm.initilialize_scene_parameters()
        bpy.ops.wm.modal_timer_operator()        
        return {'FINISHED'}

class switchModes(bpy.types.Operator):
    
    """ switch visibility modes between point cloud and terrain surface """
    
    bl_idname = "wm.switchvisibility"
    bl_label = "Switch_between_pointsCloud_and_terrain"
    
    def execute(self,context) :       
        global planeShow
        pointObj= bpy.data.objects[pointFile.split(".")[0]]  
        planeObj= bpy.data.objects[plane]
        pointObj.hide = not pointObj.hide
        planeObj.hide = not planeObj.hide
        if pointObj.hide:
           planeShow=True
        else: 
           planeShow=False
        return {'FINISHED'}   

class switchModes(bpy.types.Operator):
    
    """ switch visibility modes between point cloud and terrain surface """
    
    bl_idname = "wm.switchvisibility"
    bl_label = "Switch_between_pointsCloud_and_terrain"
    
    def execute(self,context) :       
        global planeShow
        pointObj= bpy.data.objects[pointFile.split(".")[0]]  
        planeObj= bpy.data.objects[plane]
        pointObj.hide = not pointObj.hide
        planeObj.hide = not planeObj.hide
        if pointObj.hide:
           planeShow=True
        else: 
           planeShow=False
        return {'FINISHED'}   
       
class walkthrough(bpy.types.Operator):
    
    """switch to user camera mode and runs animation walkthrough """
    
    bl_idname = "wm.walkthrough"
    bl_label = "walk_through_simulator"     
    
    def execute(self, context):
        if bpy.data.objects.get("line"):
            cameraView("Camera")
            bpy.ops.screen.animation_play()

        return {'FINISHED'} 

class elevMap(bpy.types.Operator):
    
    """switch between elevation color ramp and slope for the plane object using the Node analysis GIS blender aaddon """
    
    bl_idname = "wm.colorramp"
    bl_label = "Draw_color_ramp"     
    
    def execute(self, context):
        
        if bpy.data.objects.get(plane) and not bpy.data.objects[plane].hide:
            obj= selectOnly(plane)
            bpy.context.scene.objects.active = obj

        # remove previous material from material slot #
            if obj.material_slots: 
                if "Height_plane" in [m.name for m in bpy.data.materials]: 
                    if obj.active_material==bpy.data.materials["Height_plane"]:
                        mat="Slope"
                    else:
                        mat="Height_plane"
                    for index,slot in enumerate(obj.material_slots):
                        bpy.ops.object.material_slot_remove() 
            try:
                bpy.ops.analysis.nodes()
                bpy.data.objects[plane].active_material=bpy.data.materials[mat]
                
            except:
                raise NameError("Cannot operate node nanalysis for the plane object")
        else:
            bpy.ops.analysis.nodes()
        return {'FINISHED'} 
    
################### GUI ###################
    
class mainPanel(bpy.types.Panel):
    
    """ Main toolbar /panel for the program """    
    
    bl_label = "TANGIBLE LANDSCAPES"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
 
    def draw(self, context):
        
        self.layout.operator("wm.file_listener", text="Turn on Watch Mode", icon="GHOST_ENABLED")
        self.layout.operator("screen.animation_play",text="Play / Stop animation", icon="ANIM"  )
        self.layout.operator("wm.switchvisibility",text=" PointCloud / Terrain", icon="TEXTURE" )
        self.layout.operator("wm.colorramp",text=" Height map / Aspect ", icon="COLOR")

        self.layout.operator("wm.walkthrough",text="Walkthrough simulation", icon="OUTLINER_DATA_POSE"  )
        self.layout.operator("view3d.object_as_camera",text="Change camera", icon="SEQUENCE"  )
        self.layout.operator("wm.execmain",text="Run / Clear Scene", icon="RIGHTARROW")
        self.layout.operator("object.dialog_operator", text="Configuration", icon="PREFERENCES" ) 

class DialogOperator(bpy.types.Operator):
    
    """ setting and preferences dialogue """
    
    bl_idname = "object.dialog_operator"
    bl_label = "Setup Initial Parameters"
 
    X_float = FloatProperty(name="x Coordinates", 
        min=-1000000, max=1000000)
    Y_float = FloatProperty(name="Y coordinates", 
        min=-1000000, max=1000000) 
    
    watch_string = StringProperty(name="Watch folder") 
    scratch_string = StringProperty(name="scratch folder")  
    point_string=  StringProperty(name="point file name") 
    cam_string = StringProperty(name="camera file name")
    plane_string = StringProperty(name="plane file name")
    DEM_string = StringProperty(name="DEM file name")
    ortho_string = StringProperty(name="Orthphoto file name")
    tree_string = StringProperty(name="tree patch file name")  
    planeShow_bool = BoolProperty(name="Point_cloud/terrain")


    def execute(self, context):
        message = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} " .format (self.X_float, self.Y_float, self.watch_string,self.scratch_string, \
        self.cam_string, self.point_string,self.plane_string, self.DEM_string, self.ortho_string, self.tree_string)
        self.report({'INFO'}, message)
        return {'FINISHED'}
    
    """ This will be used to call the dialogue after the program launches and when requested """
    
    def invoke(self, context, event):
        global xtransfer,ytransfer, watchName, scratchFolder, cameraFile , planeFile,DEMfile,orthoFile,treepatchFile, planeShow
        
        self.X_float = xtransfer
        self.Y_float = ytransfer
        self.watch_string= watchName
        self.scratch_string=scratchFolder
        self.point_string = pointFile
        self.cam_string= cameraFile
        self.plane_string= planeFile
        self.DEM_string= DEMFile
        self.ortho_string= orthoFile
        self.tree_string= treePatchFile
        self. planeShow_bool=planeShow
        
        return context.window_manager.invoke_props_dialog(self)

   
def register(module):
    
    """ registers modules and operators """
    bpy.utils.register_module(module)

def unregister(module):
    """ unregisters modules and operators """
    bpy.utils.unregister_module(module)


if __name__ == "__main__":    
    # register all Classes
    register(__name__)
    # Invoke the configuration dialog when loading
    #bpy.ops.object.dialog_operator('INVOKE_DEFAULT')
