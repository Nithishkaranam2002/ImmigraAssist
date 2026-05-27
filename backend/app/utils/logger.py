from loguru import logger

# remove default handler and add a clean one
logger.remove()
logger.add(
    "logs/immigraassist.log",
    rotation="10 MB",       # new file every 10MB
    retention="30 days",    # keep logs 30 days
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}"
)

# also log to console
logger.add(
    lambda msg: print(msg, end=""),
    level="DEBUG",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}"
)