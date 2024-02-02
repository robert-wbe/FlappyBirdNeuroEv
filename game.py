import sys
import pygame
import random
import neuralnetwork as nn

pygame.init()

SCREEN_WIDTH = 576
SCREEN_HEIGHT = 1024

class Pipe:
    HEIGHT_BUFFER = 150
    GAP_HEIGHT = 250
    img = pygame.image.load("assets/pipe-green.png")
    lower = pygame.transform.scale2x(img)
    upper = pygame.transform.flip(lower, False, True)
    def __init__(self) -> None:
        self.height = random.randint(self.HEIGHT_BUFFER, SCREEN_HEIGHT-150-self.HEIGHT_BUFFER)
        self.lowerRect = self.lower.get_rect()
        self.lowerRect.topleft = (SCREEN_WIDTH, self.height+self.GAP_HEIGHT//2)
        self.upperRect = self.upper.get_rect()
        self.upperRect.bottomleft = (SCREEN_WIDTH, self.height-self.GAP_HEIGHT//2)
    
    def update(self):
        self.lowerRect.centerx -= 3
        self.upperRect.centerx -= 3

def normalize(val, low, high, scale: float = 1) -> float:
    return ((val-low)/(high-low)-0.5)*2*scale

class Bird:
    GRAVITY = 0.5
    JUMP_STRENGTH = 12

    def __init__(self, initialY=SCREEN_HEIGHT//2, isYellow=False) -> None:
        self.isActive = True
        self.yVelocity = 0
        img = pygame.image.load("assets/yellowbird-midflap.png").convert_alpha() if isYellow else pygame.image.load("assets/bluebird-midflap.png").convert_alpha()
        self.img = pygame.transform.scale2x(img)
        self.rect = self.img.get_rect(center=(100, initialY))
        self.network = nn.NeuralNetwork(5, 5, 2)
    
    def checkCollision(self, pipes: list[Pipe]):
        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_HEIGHT-100:
            return True
        for pipe in pipes:
            if self.rect.colliderect(pipe.lowerRect) or self.rect.colliderect(pipe.upperRect):
                return True
    
    def jump(self):
        self.yVelocity = -self.JUMP_STRENGTH
    
    def update(self):
        self.yVelocity += self.GRAVITY
        self.rect.centery += self.yVelocity
    
    def think(self, nextPipe: Pipe):
        normalYPos = normalize(self.rect.centery, 0, SCREEN_HEIGHT)
        normalYVel = normalize(self.yVelocity, -30, 30, scale=0.05)
        normalPipeX = normalize(nextPipe.lowerRect.centerx, SCREEN_WIDTH/2, SCREEN_WIDTH, scale=0.05)
        normalPipeLow = normalize(nextPipe.upperRect.bottom, 0, SCREEN_HEIGHT)
        normalPipeHigh = normalize(nextPipe.lowerRect.top, 0, SCREEN_HEIGHT)
        results = self.network.run([normalYPos, normalYVel, normalPipeX, normalPipeLow, normalPipeHigh])
        if results[1] > results[0]:
            self.jump()
        
    def mutate(self, amount: float=0.3):
        new = Bird()
        new.network = self.network.mutated(random.random()*amount)
        return new
    
class UIButton:
    FLAPPY_BIRD_FONT = pygame.font.SysFont("Impact", 32)

    def __init__(self, action, rect: pygame.Rect, text="", img="") -> None:
        self.action = action
        self.rect: pygame.Rect = rect
        if text: self.textObj = self.FLAPPY_BIRD_FONT.render(text, True, (0, 0, 0))
        self.img: pygame.image = pygame.image.load(img)
    
    def draw(self, screen: pygame.Surface):
        if self.img:
            screen.blit(self.img, self.rect)
        else:
            pygame.draw.rect(screen, (255, 255, 255), self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, width=5)
        if self.textObj:
            screen.blit(self.textObj, self.rect)

    def handleClick(self, pos: (int, int)) -> bool:
        """Handle click and return true if action invoked"""
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False

def drawNeuralNetwork(screen: pygame.Surface, network: nn.NeuralNetwork, x: int, y: int, width: int, height: int):
    NODE_RADIUS = 10

    shape, size = network.shape, network.size
    for j, inp in enumerate(network.netinputs):
        pygame.draw.circle(screen, (255, 255, 255), (x+width/(size+1), y+(j+1)*height/(shape[0]+1)), NODE_RADIUS)
        pygame.draw.circle(screen, (227-inp*27, 152-inp*102, 227-inp*27), (x+width/(size+1), y+(j+1)*height/(shape[0]+1)), NODE_RADIUS, width=3)

    for i, layer in enumerate(network.layers):
        for j, out in enumerate(layer.output):
            pygame.draw.circle(screen, (255, 255, 255), (x+(i+2)*width/(size+1), y+(j+1)*height/(shape[i+1]+1)), NODE_RADIUS)
            pygame.draw.circle(screen, (255*(1-out), 255-out*205, 255), (x+(i+2)*width/(size+1), y+(j+1)*height/(shape[i+1]+1)), NODE_RADIUS, width=3)

class FlappyBirdAIGame:
    FPS = 60
    GENERATION_SIZE = 10
    FLAPPY_BIRD_FONT = pygame.font.SysFont("Impact", 32)
    SIM_SPEEDS = (1,4,16)
    speedButtonRects = (pygame.Rect(320, 60, 65, 32), pygame.Rect(405, 60, 65, 32), pygame.Rect(490, 60, 65, 32))
    speedButtonImgs = (pygame.image.load("assets/normal-speed.png"), pygame.image.load("assets/medium-speed.png"), pygame.image.load("assets/full-speed.png"))

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.simulationSpeed = 1
        self.gameTime = 1
        self.groundX = 0
        self.highScore = 0
        self.generation = 1

        background = pygame.image.load("assets/background-day.png").convert()
        self.background = pygame.transform.scale2x(background)
        ground = pygame.image.load("assets/base.png").convert()
        self.ground = pygame.transform.scale2x(ground)
        pipe = pygame.image.load("assets/pipe-green.png").convert()
        self.pipe = pygame.transform.scale2x(pipe)

        self.pipes: list[Pipe] = [Pipe()]
        self.birds: list[Bird] = [Bird() for _ in range(self.GENERATION_SIZE)]
        self.bestBird = self.birds[0]
    
    def newGen(self):
        self.birds = [self.bestBird.mutate() for _ in range(self.GENERATION_SIZE)]
        self.pipes = [Pipe()]
        self.gameTime = 1
        self.generation += 1

    def draw(self):
        self.screen.blit(self.background, (0,0))
        for pipe in self.pipes:
            self.screen.blit(pipe.lower, pipe.lowerRect)
            self.screen.blit(pipe.upper, pipe.upperRect)
        self.screen.blit(self.ground, (-self.groundX,900))
        for bird in self.birds:
            if bird.isActive:
                self.screen.blit(bird.img, bird.rect)
        timeAlive = self.FLAPPY_BIRD_FONT.render(f"TIME ALIVE: {self.gameTime//self.FPS}", True, (0,0,0))
        highScore = self.FLAPPY_BIRD_FONT.render(f"BEST AI: {self.highScore//self.FPS}", True, (0,0,0))
        speedChooser = self.FLAPPY_BIRD_FONT.render(f"SIMULATION SPEED", True, (0,0,0))
        genCounter = self.FLAPPY_BIRD_FONT.render(f"GEN {self.generation}", True, (0,0,0))
        self.screen.blit(timeAlive, (20, 20))
        self.screen.blit(highScore, (20, 60))
        self.screen.blit(speedChooser, (320, 20))
        self.screen.blit(genCounter, (215, 20))
        drawNeuralNetwork(self.screen, self.focusBird.network, 400, 700, 200, 150)

        for i in range(3):
            self.screen.blit(self.speedButtonImgs[i], self.speedButtonRects[i])

        pygame.display.update()
    
    def update(self):
        self.gameTime += 1
        if self.gameTime > self.highScore:
            self.highScore = self.gameTime
        stop = True
        self.groundX = ((self.groundX + 3) % 48)
        if self.gameTime % 120 == 0:
            if len(self.pipes) >= 3:
                self.pipes.pop(0)
            self.pipes.append(Pipe())
        for pipe in self.pipes:
            pipe.update()
        for bird in self.birds:
            if bird.isActive:
                if bird.checkCollision(self.pipes):
                    bird.isActive = False
                    self.bestBird = bird
                    continue
                stop = False
                self.focusBird = bird
                nextPipe = self.pipes[-2] if len(self.pipes) > 1 and self.pipes[-2].lowerRect.right >= bird.rect.left else self.pipes[-1]
                bird.think(nextPipe)
                bird.update()
        if stop:
            self.newGen()
            self.update()
    
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    for i in range(3):
                        if self.speedButtonRects[i].collidepoint(pos):
                            self.simulationSpeed = self.SIM_SPEEDS[i]
                            break
                # if event.type == pygame.KEYDOWN:
                #     if event.key == pygame.K_SPACE:
                #         pass
            for _ in range(self.simulationSpeed):
                self.update()
            self.draw()
            self.clock.tick(self.FPS)
    

if __name__ == "__main__":
    FlappyBirdAIGame().run()