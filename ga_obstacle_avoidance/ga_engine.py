import random

from ga_obstacle_avoidance.ga_robot import GaRobot
from sensor.proximity_sensor import ProximitySensor
from robot.actuator import Actuator
from robot.motor_controller import MotorController
from ga_obstacle_avoidance.genome import Genome


ROBOT_SIZE = 25
OBSTACLE_SENSOR_ERROR = 0
ELITISM_NUM = 3
SELECTION_PERCENTAGE = 0.3  # 0 < SELECTION_PERCENTAGE < 1
MUTATION_PROBABILITY = 0.3  # 0 < MUTATION_PROBABILITY < 1
MUTATION_COEFFICIENT = 0.07


class GaEngine:

    def __init__(self, scene, population_num):
        if population_num <= ELITISM_NUM:
            raise ValueError('Error: population_num (' + str(population_num) + ') must be greater than ELITISM_NUM (' + str(
                ELITISM_NUM) + ')')

        self.scene = scene
        self.population_num = population_num
        self.robots = []
        self.genomes = []
        self.genomes_last_generation = []
        self.best_genome = None
        self.generation_num = 1

        for i in range(self.population_num):
            x, y = self.robot_start_position()
            genome = Genome.random(self.generation_num)
            self.genomes.append(genome)
            robot = self.build_robot(x, y, genome, None)
            scene.put(robot)
            self.robots.append(robot)

        print('\nGeneration', self.generation_num, 'started')

    def step(self):
        for robot in self.robots:
            robot.sense_and_act()

            # ensure robot doesn't accidentaly go outside of the scene
            if robot.x < 0 or robot.x > self.scene.width or robot.y < 0 or robot.y > self.scene.height:
                self.destroy_robot(robot)

            # destroy robot if it collides an obstacle
            if robot.collision_with_object:
                self.destroy_robot(robot)

            # check population extinction
            if not self.robots:
                print('Generation', self.generation_num, 'terminated')
                self.create_new_generation()

    def build_robot(self, x, y, genome, label):
        robot = GaRobot(x, y, ROBOT_SIZE, genome)
        robot.direction = 0
        robot.label = label

        left_obstacle_sensor = ProximitySensor(robot, genome.sensor_delta_direction, genome.sensor_saturation_value,
                                               OBSTACLE_SENSOR_ERROR, genome.sensor_max_distance, self.scene)
        right_obstacle_sensor = ProximitySensor(robot, -genome.sensor_delta_direction, genome.sensor_saturation_value,
                                                OBSTACLE_SENSOR_ERROR, genome.sensor_max_distance, self.scene)
        left_wheel_actuator = Actuator()
        right_wheel_actuator = Actuator()
        left_motor_controller = MotorController(left_obstacle_sensor, genome.motor_ctrl_coefficient,
                                                left_wheel_actuator, genome.motor_ctrl_min_actuator_value)
        right_motor_controller = MotorController(right_obstacle_sensor, genome.motor_ctrl_coefficient,
                                                 right_wheel_actuator, genome.motor_ctrl_min_actuator_value)

        robot.set_left_motor_controller(left_motor_controller)
        robot.set_right_motor_controller(right_motor_controller)

        return robot

    def destroy_robot(self, robot):
        # save fitness value
        fitness_value = robot.mileage
        robot.genome.fitness = fitness_value

        self.scene.remove(robot)
        self.robots.remove(robot)
        # print('Destroyed robot with fitness value', fitness_value)

    def create_new_generation(self):
        self.genomes_last_generation = self.genomes
        genomes_selected = self.ga_selection()  # parents of the new generation
        # print("\ngenomes selected", genomes_selected)
        self.generation_num += 1
        new_genomes = self.ga_crossover_mutation(genomes_selected)
        self.genomes = new_genomes

        # draw a label for the elite individuals
        elite_label = 1

        for genome in self.genomes:
            if elite_label <= ELITISM_NUM:
                label = elite_label
                elite_label += 1
            else:
                label = None

            x, y = self.robot_start_position()
            robot = self.build_robot(x, y, genome, label)
            self.scene.put(robot)
            self.robots.append(robot)

        print('\nGeneration', self.generation_num, 'started')

    def ga_selection(self):
        # sort genomes by fitness
        sorted_genomes = sorted(self.genomes, key=lambda genome: genome.fitness, reverse=True)
        best_genome_current_generation = sorted_genomes[0]

        if self.best_genome is None or best_genome_current_generation.fitness > self.best_genome.fitness:
            self.best_genome = best_genome_current_generation
            print('New best:', self.best_genome.to_string())

        num_genomes_to_select = round(self.population_num * SELECTION_PERCENTAGE)
        genomes_selected = []

        # elitism: keep the best genomes in the new generation
        for i in range(ELITISM_NUM):
            elite_genome = sorted_genomes.pop(0)
            genomes_selected.append(elite_genome)
            num_genomes_to_select -= 1
            print("Elite:", elite_genome.to_string())

        while num_genomes_to_select > 0:
            genome_selected = self.roulette_select(sorted_genomes)
            genomes_selected.append(genome_selected)
            sorted_genomes.remove(genome_selected)
            num_genomes_to_select -= 1

        return genomes_selected

    def roulette_select(self, genomes):
        fitness_sum = 0

        for genome in genomes:
            fitness_sum += genome.fitness

        value = random.uniform(0, fitness_sum)

        for i in range(len(genomes)):
            value -= genomes[i].fitness

            if value < 0:
                return genomes[i]

        return genomes[-1]

    def ga_crossover_mutation(self, parents):
        num_genomes_to_create = self.population_num
        new_genomes = []

        # elitism: keep the best genomes in the new generation
        for i in range(ELITISM_NUM):
            new_genomes.append(parents[i])
            num_genomes_to_create -= 1

        while num_genomes_to_create > 0:
            parent_a, parent_b = self.choose_parents(parents)
            new_genome = parent_a.crossover(parent_b, self.generation_num)
            new_genome.mutation(MUTATION_PROBABILITY, MUTATION_COEFFICIENT)
            new_genomes.append(new_genome)
            num_genomes_to_create -= 1

        return new_genomes

    def choose_parents(self, parents):
        pos_a = random.randrange(len(parents))
        parent_a = parents[pos_a]
        parents.remove(parent_a)  # avoid choosing the same parent two times
        pos_b = random.randrange(len(parents))
        parent_b = parents[pos_b]
        parents.insert(pos_a, parent_a)  # reinsert the first parent in the list
        return parent_a, parent_b

    def robot_start_position(self):
        x = self.scene.width / 2
        y = self.scene.height / 2
        return x, y
