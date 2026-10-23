#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <gazebo/physics/ContactManager.hh>
#include <gazebo/physics/Contact.hh>
#include <gazebo/sensors/SensorsIface.hh>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <string>

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  gazebo::setupServer();
  auto world = gazebo::loadWorld(argv[1]);
  if (!world) return 3;
  // Server::Run initializes sensors before World::Step loads world plugins.
  // Loading the buoyancy plugin manually here would apply its forces twice.
  gazebo::sensors::run_once(true);
  gazebo::sensors::run_threads();
  auto cm = world->Physics()->GetContactManager();
  cm->SetNeverDropContacts(true);
  std::map<std::string, std::set<std::string>> contacts;
  std::map<std::string, double> maximumSpeed;
  bool finite = true;
  auto event = gazebo::event::Events::ConnectWorldUpdateEnd([&]() {
    for (unsigned i = 0; i < cm->GetContactCount(); ++i) {
      auto c = cm->GetContact(i);
      for (int k = 0; k < 2; ++k) {
        auto a = k ? c->collision2 : c->collision1;
        auto b = k ? c->collision1 : c->collision2;
        if (a->GetModel()->GetName().find("probe_") == 0)
          contacts[a->GetModel()->GetName()].insert(b->GetScopedName());
      }
    }
    for (auto m : world->Models()) {
      if (m->GetName().find("probe_") != 0) continue;
      auto p = m->WorldPose().Pos();
      auto v = m->WorldLinearVel();
      finite &= p.IsFinite() && v.IsFinite();
      maximumSpeed[m->GetName()] = std::max(maximumSpeed[m->GetName()], v.Length());
    }
  });
  const auto start = std::chrono::steady_clock::now();
  gazebo::runWorld(world, 20000);
  double wallSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  event.reset();
  std::cout << std::setprecision(12) << "WORLD_RESULT {\"simulated_s\":"
            << world->SimTime().Double() << ",\"wall_s\":" << wallSeconds
            << ",\"model_count\":" << world->ModelCount()
            << ",\"all_trajectories_finite\":" << (finite ? "true" : "false")
            << ",\"probes\":[";
  bool first = true;
  for (auto m : world->Models()) {
    if (m->GetName().find("probe_") != 0) continue;
    if (!first) std::cout << ',';
    first = false;
    const auto p = m->WorldPose().Pos();
    std::cout << "{\"name\":\"" << m->GetName() << "\",\"x\":" << p.X()
              << ",\"y\":" << p.Y() << ",\"z\":" << p.Z()
              << ",\"speed\":" << m->WorldLinearVel().Length()
              << ",\"maximum_speed\":" << maximumSpeed[m->GetName()]
              << ",\"contacts\":[";
    bool f = true;
    for (const auto &n : contacts[m->GetName()]) {
      if (!f) std::cout << ',';
      f = false;
      std::cout << '"' << n << '"';
    }
    std::cout << "]}";
  }
  std::cout << "],\"rays\":[";
  auto ray = boost::dynamic_pointer_cast<gazebo::physics::RayShape>(
      world->Physics()->CreateShape("ray", gazebo::physics::CollisionPtr()));
  std::ifstream inputs(argv[2]);
  std::string name;
  double ax, ay, az, bx, by, bz;
  first = true;
  while (inputs >> name >> ax >> ay >> az >> bx >> by >> bz) {
    ray->SetPoints({ax, ay, az}, {bx, by, bz});
    double distance = -1;
    std::string entity;
    ray->GetIntersection(distance, entity);
    if (!first) std::cout << ',';
    first = false;
    std::cout << "{\"name\":\"" << name << "\",\"distance\":" << distance
              << ",\"entity\":\"" << entity << "\"}";
  }
  std::cout << "]}" << std::endl;
  ray.reset();
  world.reset();
  gazebo::shutdown();
  return finite ? 0 : 4;
}
