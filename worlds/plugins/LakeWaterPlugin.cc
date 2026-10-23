// SPDX-License-Identifier: MIT
// Gazebo Classic 11: local collision-union voxel buoyancy in bounded lakes.
#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <gazebo/common/common.hh>
#include <gazebo/physics/BoxShape.hh>
#include <gazebo/physics/SphereShape.hh>
#include <gazebo/physics/CylinderShape.hh>
#include <ignition/math/Vector2.hh>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <sstream>
#include <vector>

namespace gazebo
{
using V3 = ignition::math::Vector3d;
using V2 = ignition::math::Vector2d;
using Pose = ignition::math::Pose3d;
namespace
{
double Clamp(double v, double lo, double hi) { return std::max(lo, std::min(hi, v)); }
struct Lake
{
  std::string name;
  double level = 0, bottom = -10;
  std::vector<V2> polygon;
  V2 lo{1e100, 1e100}, hi{-1e100, -1e100};
  bool Contains(double x, double y) const
  {
    if (x < lo.X() || x > hi.X() || y < lo.Y() || y > hi.Y()) return false;
    bool inside = false;
    for (size_t i = 0, j = polygon.size() - 1; i < polygon.size(); j = i++)
    {
      const auto &a = polygon[i]; const auto &b = polygon[j];
      if ((a.Y() > y) != (b.Y() > y) &&
          x < (b.X() - a.X()) * (y - a.Y()) / (b.Y() - a.Y()) + a.X())
        inside = !inside;
    }
    return inside;
  }
  double BoundaryDistanceSquared(double x, double y) const
  {
    const V2 p(x,y); double best=1e100;
    for(size_t i=0,j=polygon.size()-1;i<polygon.size();j=i++){
      const V2 a=polygon[j],b=polygon[i],edge=b-a;
      const double t=Clamp((p-a).Dot(edge)/std::max(1e-20,edge.SquaredLength()),0,1);
      best=std::min(best,(p-(a+edge*t)).SquaredLength());
    }
    return best;
  }
};
struct Geometry
{
  enum Type { BOX, SPHERE, CYLINDER } type = BOX;
  Pose pose;
  V3 half;
  double radius = 0, length = 0;
  bool Contains(const V3 &p) const
  {
    V3 q = pose.Rot().RotateVectorReverse(p - pose.Pos());
    if (type == SPHERE) return q.SquaredLength() <= radius * radius;
    if (type == CYLINDER) return q.X()*q.X()+q.Y()*q.Y() <= radius*radius && std::abs(q.Z()) <= length/2;
    return std::abs(q.X()) <= half.X() && std::abs(q.Y()) <= half.Y() && std::abs(q.Z()) <= half.Z();
  }
};
struct Samples
{
  physics::LinkPtr link;
  std::vector<V3> points;
  V3 step;
  double cellVolume = 0, volume = 0, radius = 0;
};
}

class LakeWaterPlugin : public WorldPlugin
{
 public: void Load(physics::WorldPtr w, sdf::ElementPtr sdf) override
 {
   world = w;
   if (sdf->HasElement("density")) density = sdf->Get<double>("density");
   if (sdf->HasElement("linear_drag")) linearDrag = sdf->Get<double>("linear_drag");
   if (sdf->HasElement("quadratic_drag")) quadraticDrag = sdf->Get<double>("quadratic_drag");
   if (sdf->HasElement("angular_drag")) angularDrag = sdf->Get<double>("angular_drag");
   if (sdf->HasElement("samples_per_axis")) resolution = sdf->Get<int>("samples_per_axis");
   density = Clamp(density, 1, 2000); linearDrag = std::max(0.0, linearDrag);
   quadraticDrag = std::max(0.0, quadraticDrag); angularDrag = std::max(0.0, angularDrag);
   resolution = std::max(4, std::min(32, resolution));
   if (sdf->HasElement("lake"))
     for (auto e = sdf->GetElement("lake"); e; e = e->GetNextElement("lake"))
     {
       Lake lake;
       lake.name = e->HasAttribute("name") ? e->Get<std::string>("name") : "lake";
       lake.level = e->Get<double>("level"); lake.bottom = e->Get<double>("bottom");
       if (e->HasElement("point"))
         for (auto p=e->GetElement("point"); p; p=p->GetNextElement("point"))
         {
           std::istringstream ss(p->Get<std::string>()); double x,y;
           if (ss >> x >> y) { lake.polygon.emplace_back(x,y); lake.lo.X(std::min(x,lake.lo.X())); lake.lo.Y(std::min(y,lake.lo.Y())); lake.hi.X(std::max(x,lake.hi.X())); lake.hi.Y(std::max(y,lake.hi.Y())); }
         }
       if (lake.polygon.size() >= 3 && lake.level > lake.bottom) lakes.push_back(lake);
       else gzerr << "[LakeWater] Invalid lake " << lake.name << "\n";
     }
   if (sdf->HasElement("diagnostics_csv"))
   {
     log.open(sdf->Get<std::string>("diagnostics_csv"));
     log << "time,link,x,y,z,vx,vy,vz,roll,pitch,yaw,total_volume,submerged_volume,buoyancy_z,drag_power\n";
   }
   connection=event::Events::ConnectWorldUpdateBegin(std::bind(&LakeWaterPlugin::Update, this));
   gzmsg << "[LakeWater] " << lakes.size() << " bounded lakes, density=" << density
         << " kg/m3; collision-union sampling " << resolution << "^3/link.\n";
 }

 private: Samples Build(physics::LinkPtr link)
 {
   Samples s; s.link = link;
   std::vector<Geometry> geom;
   V3 lo(1e100,1e100,1e100), hi(-1e100,-1e100,-1e100);
   for (auto collision : link->GetCollisions())
   {
     Geometry g; g.pose = collision->RelativePose();
     auto shape = collision->GetShape();
     if (auto b=boost::dynamic_pointer_cast<physics::BoxShape>(shape)) g.half=b->Size()/2;
     else if (auto sp=boost::dynamic_pointer_cast<physics::SphereShape>(shape))
       {g.type=Geometry::SPHERE; g.radius=sp->GetRadius(); g.half=V3(g.radius,g.radius,g.radius);}
     else if (auto c=boost::dynamic_pointer_cast<physics::CylinderShape>(shape))
       {g.type=Geometry::CYLINDER; g.radius=c->GetRadius(); g.length=c->GetLength(); g.half=V3(g.radius,g.radius,g.length/2);}
     else
     {
       // General mesh: cache a link-local envelope. Rotation later leaves its
       // volume invariant. Users can replace mesh collisions with primitives.
       const auto b=collision->BoundingBox(); const auto pose=link->WorldPose();
       V3 ml(1e100,1e100,1e100), mh(-1e100,-1e100,-1e100);
       for(int k=0;k<8;++k) {
         V3 p((k&1)?b.Max().X():b.Min().X(),(k&2)?b.Max().Y():b.Min().Y(),(k&4)?b.Max().Z():b.Min().Z());
         p=pose.Rot().RotateVectorReverse(p-pose.Pos());
         for(int a=0;a<3;++a){ml[a]=std::min(ml[a],p[a]);mh[a]=std::max(mh[a],p[a]);}
       }
       g.pose=Pose((ml+mh)/2, ignition::math::Quaterniond::Identity); g.half=(mh-ml)/2;
       gzwarn << "[LakeWater] " << collision->GetScopedName() << " uses local AABB approximation; primitive closed collision shapes give better displacement.\n";
     }
     if (!g.half.IsFinite() || g.half.Min() <= 0 || g.half.Max() > 1000) continue;
     geom.push_back(g);
     for(int k=0;k<8;++k){
       V3 p((k&1)?g.half.X():-g.half.X(),(k&2)?g.half.Y():-g.half.Y(),(k&4)?g.half.Z():-g.half.Z());
       p=g.pose.Pos()+g.pose.Rot().RotateVector(p);
       for(int a=0;a<3;++a){lo[a]=std::min(lo[a],p[a]);hi[a]=std::max(hi[a],p[a]);}
     }
   }
   if(geom.empty()) return s;
   s.step=(hi-lo)/resolution; s.cellVolume=s.step.X()*s.step.Y()*s.step.Z();
   s.radius=V3(std::max(std::abs(lo.X()),std::abs(hi.X())),
               std::max(std::abs(lo.Y()),std::abs(hi.Y())),
               std::max(std::abs(lo.Z()),std::abs(hi.Z()))).Length();
   for(int i=0;i<resolution;++i)for(int j=0;j<resolution;++j)for(int k=0;k<resolution;++k){
     V3 p=lo+V3((i+.5)*s.step.X(),(j+.5)*s.step.Y(),(k+.5)*s.step.Z());
     if(std::any_of(geom.begin(),geom.end(),[&](const Geometry &g){return g.Contains(p);}))s.points.push_back(p);
   }
   s.volume=s.points.size()*s.cellVolume;
   gzmsg << "[LakeWater] " << link->GetScopedName() << " collision-union volume=" << s.volume << " m3, " << s.points.size() << " samples.\n";
   return s;
 }

 private: void Update()
 {
   const double now=world->SimTime().Double();
   const double dt=world->Physics()->GetMaxStepSize();
   // Refresh on a modest cadence to discover runtime-inserted models. Keeping
   // only live links also permits safe model deletion/reinsertion.
   if(now < lastRefresh || now-lastRefresh >= .25)
   {
     std::map<unsigned int,Samples> current;
     for(auto model:world->Models()) if(!model->IsStatic())
       for(auto link:model->GetLinks()) if(!link->IsStatic() && link->GetInertial()->Mass()>0){
         const auto id=link->GetId(); auto it=samples.find(id);
         current.emplace(id,it==samples.end()?Build(link):it->second);
       }
     samples.swap(current);lastRefresh=now;
   }
   bool logNow=log.is_open() && (now-lastLog>=.1 || now<lastLog);
   for(auto &entry:samples)
   {
     Samples &s=entry.second;auto link=s.link;
     const auto pose=link->WorldPose(); const auto cog=link->WorldCoGPose().Pos();
     double volume=0;V3 weighted(0,0,0);
     // Local voxel projected thickness gives continuous surface crossing.
     V3 ez=pose.Rot().RotateVectorReverse(V3::UnitZ);
     double thick=std::abs(ez.X())*s.step.X()+std::abs(ez.Y())*s.step.Y()+std::abs(ez.Z())*s.step.Z();
     thick=std::max(1e-6,thick);
     for(const auto &lake:lakes)
     {
       if(pose.Pos().X()+s.radius < lake.lo.X() || pose.Pos().X()-s.radius > lake.hi.X() ||
          pose.Pos().Y()+s.radius < lake.lo.Y() || pose.Pos().Y()-s.radius > lake.hi.Y() ||
          pose.Pos().Z()-s.radius > lake.level || pose.Pos().Z()+s.radius < lake.bottom) continue;
       const bool centerInside=lake.Contains(pose.Pos().X(),pose.Pos().Y());
       const bool awayFromBank=lake.BoundaryDistanceSquared(pose.Pos().X(),pose.Pos().Y()) > s.radius*s.radius;
       if(awayFromBank && !centerInside)continue;
       const bool allInside=awayFromBank && centerInside;
       for(const auto &local:s.points)
       {
         V3 p=pose.Pos()+pose.Rot().RotateVector(local);
         if(!allInside && !lake.Contains(p.X(),p.Y()))continue;
         const double a=Clamp((lake.level-p.Z())/thick+.5,0,1);
         const double b=Clamp((lake.bottom-p.Z())/thick+.5,0,1);
         double v=(a-b)*s.cellVolume;
         if(v<=0)continue;
         // For upright voxels use centroid of their submerged vertical span;
         // for tilted voxels this remains an explicit volume approximation.
         p.Z((std::max(p.Z()-thick/2,lake.bottom)+std::min(p.Z()+thick/2,lake.level))/2);
         volume+=v;weighted+=p*v;
       }
     }
     V3 buoyancy(0,0,0),drag(0,0,0),torque(0,0,0);
     const V3 velocity=link->WorldCoGLinearVel();
     if(volume>0)
     {
       buoyancy=-world->Gravity()*density*volume;
       link->AddForceAtWorldPosition(buoyancy,weighted/volume);
       const double area=std::pow(volume,2.0/3.0),speed=velocity.Length();
       double dragFactor=density*(linearDrag*volume+.5*quadraticDrag*area*speed);
       // A forward Euler damping force cannot remove >45% of momentum/step.
       dragFactor=std::min(dragFactor,.45*link->GetInertial()->Mass()/dt);
       drag=-velocity*dragFactor;link->AddForce(drag);
       const auto inertia=link->GetInertial();
       const double minI=std::max(1e-9,std::min({inertia->IXX(),inertia->IYY(),inertia->IZZ()}));
       double damping=angularDrag*density*volume*s.radius*s.radius/3;
       damping=std::min(damping,.45*minI/dt);
       torque=-link->WorldAngularVel()*damping;link->AddTorque(torque);
     }
     if(logNow){const auto rpy=pose.Rot().Euler();log<<std::setprecision(10)<<now<<','<<link->GetScopedName()<<','<<cog.X()<<','<<cog.Y()<<','<<cog.Z()<<','<<velocity.X()<<','<<velocity.Y()<<','<<velocity.Z()<<','<<rpy.X()<<','<<rpy.Y()<<','<<rpy.Z()<<','<<s.volume<<','<<volume<<','<<buoyancy.Z()<<','<<drag.Dot(velocity)+torque.Dot(link->WorldAngularVel())<<'\n';}
   }
   if(logNow){lastLog=now;log.flush();}
 }
 private: physics::WorldPtr world;
 private: event::ConnectionPtr connection;
 private: std::vector<Lake> lakes;
 private: std::map<unsigned int,Samples> samples;
 private: double density=1000,linearDrag=.7,quadraticDrag=1,angularDrag=1.5;
 private: int resolution=12;
 private: double lastRefresh=-1,lastLog=-1;
 private: std::ofstream log;
};
GZ_REGISTER_WORLD_PLUGIN(LakeWaterPlugin)
}
