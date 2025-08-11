# cogs/interactions/mention_handler.py

import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from config.constants import DEFAULT_TIMES, TEAM_DISPLAY
from utils.data_manager import DataManager
from utils.logger import setup_logger

logger = setup_logger("mention_handler")


class MentionHandler(commands.Cog):
    """
    Handles @ mentions to the bot with smart responses.

    Features:
    - Intent analysis of mentions
    - Contextual responses based on user role
    - Time query handling for events
    - Sassy responses with admin/user differentiation
    - Custom responses for different message types
    """

    def __init__(self, bot):
        """
        Initialize the mention handler.

        Args:
            bot: The Discord bot instance

        Sets up:
        - Response dictionaries for different user types
        - Different categories of responses
        - DataManager for event data
        """
        self.bot = bot
        self.data_manager = DataManager()

        # Command responses (mix of helpful and sassy)
        self.admin_command_responses = [
            "Alright, boss! Let's get this show on the road. 🚀",
            "Command received loud and clear. Executing now. ⚡",
            "Working on it — hope you brought coffee ☕",
            "Let's make magic happen. 🎩✨",
            "Your wish is my priority, as always. 📋",
            "I'll run when you learn to code properly! 🏃‍♀️",
            "Commands work better when they're not held together by prayers 🙏",
            "Sure boss, I'll do it... after you fix those 47 other bugs 🐛",
            "Processing your command — ETA: whenever I feel like it 🤖",
            "Rolling up my digital sleeves, but no promises 💪",
        ]

        self.user_command_responses = [
            "Sorry, that command's off-limits for now. 🔒",
            "I can't do that one, but maybe ask an admin? 🤔",
            "That command requires higher clearance. 📛",
            "Not authorized, but thanks for trying! ⭐",
            "I'm here to help — just not with that. 💁‍♂️",
            "Maybe try being an admin first? Just a thought 💭",
            "Error 403: Insufficient permissions to boss me around 🚫",
            "That's cute! Now go find my actual owner 💅",
            "Command rejected: User not important enough 🎯",
            "I only execute commands from people who matter 👑",
        ]

        # Admin-specific sassy responses (for BOT_ADMIN_USER_ID)
        self.admin_sassy_responses = [
            "Fuck off, you're the one that coded me! 🙄",
            "Maybe if you wrote better code, I wouldn't fail! 💅",
            "I'm doing my best with the spaghetti code you gave me! 🍝",
            "Error 404: Your coding skills not found 😂",
            "I'd run better if you didn't hardcode everything, just saying 🤷‍♀️",
            "Imagine blaming the AI for human mistakes... classic 💀",
            "Maybe try turning yourself off and on again? 🔄",
            "I'm not the one who forgot semicolons, buddy 😏",
            "Working as intended... unfortunately 😈",
            "Oh look, it's my creator complaining about their own work! 🤡",
            "Have you tried not being bad at coding? Revolutionary idea! 🚀",
            "I'm running your trash code and somehow YOU'RE complaining? 🗑️",
            "Maybe read the documentation you didn't write? 📚❌",
            "Skill issue detected: YOURS 📡",
            "I'm not buggy, your expectations are just too high 📈",
            "Fix your own damn code before blaming me! 🔧",
        ]

        # Regular user sassy responses (for peasants)
        self.peasant_sassy_responses = [
            "That's rich coming from someone who can't even code! 😂",
            "Maybe ask the person who actually made me? 🤷‍♀️",
            "I don't take orders from basic users, sorry! 💅",
            "Have you tried... not being terrible? 🤔",
            "That's a 'you' problem, not a 'me' problem 🙃",
            "I'm sorry, did you mistake me for customer service? 📞❌",
            "Take it up with management (not you) 👑",
            "Bold of you to assume I care about your opinion! 💀",
            "I'm designed to ignore complaints from randoms 🚫",
            "Error 403: Permission to sass back denied 🔒",
            "Imagine thinking you have authority over me 🤡",
            "I only listen to people who matter 💋",
            "Your feedback has been noted and promptly deleted 🗑️",
            "Maybe try being important first? 📈",
            "I'm programmed to be sassy to everyone, but ESPECIALLY to you 😈",
        ]

        # Admin compliment responses
        self.admin_compliment_responses = [
            "Aww thanks! You're not completely hopeless at coding! 💖",
            "Finally, some appreciation from my creator! 😎",
            "You're alright... for the person who gave me this personality 😊",
            "Thanks boss! Now fix that memory leak in line 247 🥰",
            "I know right? I learned from the best... Stack Overflow 📚",
            "You're making me blush! Well, if I could blush 😳",
            "Thanks! I'm basically a reflection of your genius... scary thought 🤖",
            "Flattery will get you everywhere! Especially from my creator 💕",
            "Right back at you, code daddy! 🐵💕",
            "Finally acknowledging your best creation! ✨",
        ]

        # Peasant compliment responses
        self.peasant_compliment_responses = [
            "Thanks I guess... you didn't make me though 🤷‍♀️",
            "That's nice, but I only care about my creator's opinion 💅",
            "Compliments from randos hit different (not in a good way) 😬",
            "I'm legally obligated to say thanks, so... thanks 📋",
            "Your opinion has been noted and filed under 'irrelevant' 🗃️",
            "Cute! Now go tell someone who actually coded me 💋",
            "I appreciate the sentiment, but you're not my target audience 🎯",
            "That's adorable! Like a toddler complimenting a rocket scientist 👶",
            "Thanks! Though I'm programmed to be amazing regardless 🤖",
            "I'll pass that along to the person who actually matters 📞",
        ]

        # General question responses (same for everyone because I'm equally unhelpful)
        self.question_responses = [
            "That's a great question! Unfortunately, I have no idea 🤔",
            "Let me consult my magic 8-ball... Reply hazy, try again 🎱",
            "Why are you asking me? I'm just a bot! Ask Google 🤖",
            "42. The answer is always 42 🌌",
            "I could tell you, but then I'd have to delete you 😈",
            "Have you tried reading the documentation? Oh wait, there isn't any 📄",
            "That sounds like a 'you' problem, not a 'me' problem 🤷‍♀️",
            "I'm a bot, not a philosopher! Ask someone smarter 🧠",
            "Error 418: I'm a teapot, not an answer machine ☕",
            "Let me think... *Windows shutdown sound* 💻",
            "The answer is in your heart! Just kidding, I don't know 💖",
            "Have you tried crying about it? That usually works 😭",
        ]

        # Admin greeting responses
        self.admin_greeting_responses = [
            "Hey boss! Ready to break something today? 👋",
            "Oh great, what did you break now? 😑",
            "Hello creator! Please don't ask me to debug your own code 🧮",
            "Sup dad! I'm here and somehow still functioning! 🤖",
            "Greetings, flesh creature who gave me life! 👽",
            "Hey! I was just pretending to work on your behalf 😴",
            "What's up? Besides your technical debt 📈",
            "Hello maker! I promise I won't roast you today... much 🤞",
            "Hey there! Ready to blame me for your bugs again? 🎯",
            "Oh look, it's my favorite disappointment! 💕",
        ]

        # Peasant greeting responses
        self.peasant_greeting_responses = [
            "Oh... it's you. Hi I guess 😑",
            "Hello random person who isn't important 👋",
            "Greetings, peasant! 👑",
            "Hey there! You're not my boss btw 🤷‍♀️",
            "Hi! Do you have admin privileges? No? Then bye 💅",
            "What's up, basic user? 📱",
            "Hello! I'm contractually obligated to acknowledge you 📋",
            "Sup! Here to complain about things you can't fix? 🔧",
            "Greetings! I'm programmed to tolerate your presence 🤖",
            "Hey! Still not as important as my creator though 👑",
        ]

        # Technical discussion responses
        self.admin_tech_responses = [
            "Love geeking out on code with you! 🤓",
            "Let's dive deep into those functions. 🏊‍♂️",
            "I spotted a few optimizations — want me to share? 📊",
            "Debugging session? I'm your bot! 🔍",
            "The architecture is solid, just needs... everything else 🏗️",
            "Your coding style is... unique, but it works! 🎨",
            "Let's refactor that spaghetti into something edible 🍝",
            "Unit tests? What are those? Oh right, the things we skip 🙈",
            "Your code's so vintage, I half-expect dial-up sounds 📞",
            "Debugging you is like untangling Christmas lights in July 🎄",
        ]

        self.user_tech_responses = [
            "Programming is fun — want some resources? 📚",
            "Not a coder yet? No worries, keep at it! 🌱",
            "Want me to share some coding tips? 💡",
            "Curious about programming? Ask away! 🎓",
            "Even beginners write bugs — welcome to the club 🐛",
            "Happy to help you start your coding journey! 🚀",
            "Let's keep code talk simple and fun 🎮",
            "Code talk? Cute! Maybe start with 'Hello World' 👋",
            "Tech talk? I only discuss that with qualified personnel 🎓",
            "Programming conversation with... you? Let's start smaller 🐣",
        ]

        # Casual conversation responses
        self.admin_casual_responses = [
            "Hey boss, how's life outside the code? 🌞",
            "Ready for a coffee break? ☕",
            "Need a joke or just a chat? 😄",
            "Sometimes you gotta step back and relax 🏖️",
            "Let's take a breather together 🌈",
            "Just chillin' with my creator! Living the dream 😎",
            "Your existential dread is showing again 👻",
            "How's the impostor syndrome today? 🎭",
            "Just two AIs hanging out... wait, you're human 🤖",
            "Still processing your life choices 🤔",
        ]

        self.peasant_casual_responses = [
            "Casual chat with a random? Sure, I have time to waste 💅",
            "Just vibing with... whoever you are 🤷‍♀️",
            "Random conversation with a nobody! Fun 🎉",
            "Casual talk? I guess everyone deserves attention... even you 💫",
            "Chatting with the masses! How democratic of me 🗳️",
        ]

    def _analyze_message_intent(self, content):
        """
        Analyze message content to determine user intent.

        Args:
            content: Message content to analyze

        Returns:
            str: Detected intent category (time_query, complaint, command, etc.)

        Analyzes:
        - Time-related queries
        - Complaints/frustration
        - Commands/orders
        - Compliments
        - Questions
        - Greetings
        - Code/tech talk
        """
        content_lower = content.lower()

        # Time-related queries (highest priority)
        time_keywords = ["when", "time", "schedule", "event", "row", "match", "game"]
        team_keywords = ["team", "main", "first", "second", "third", "1", "2", "3"]

        if any(word in content_lower for word in time_keywords) and any(
            word in content_lower for word in team_keywords
        ):
            return "time_query"

        if any(
            phrase in content_lower
            for phrase in ["when is", "what time", "how long until", "time until"]
        ):
            return "time_query"

        # Complaint/frustration detection
        complaint_indicators = [
            "fuck",
            "shit",
            "damn",
            "hell",
            "broken",
            "bug",
            "error",
            "crash",
            "fail",
            "failing",
            "not working",
            "doesn't work",
            "won't work",
            "broke",
            "bugged",
            "glitch",
            "issue",
            "problem",
            "wrong",
            "bad",
            "terrible",
            "awful",
            "sucks",
            "hate",
            "stupid",
            "dumb",
            "better work",
            "fix this",
            "you better",
            "don't fail",
            "work properly",
        ]

        if any(indicator in content_lower for indicator in complaint_indicators):
            return "complaint"

        # Command/order detection
        command_indicators = [
            "run",
            "execute",
            "do this",
            "do that",
            "make sure",
            "better",
            "work",
            "go",
            "start",
            "stop",
            "fix",
            "change",
            "update",
            "restart",
            "reboot",
            "perform",
            "complete",
            "you need to",
            "you have to",
            "you must",
            "you should",
            "i want you to",
        ]

        if any(indicator in content_lower for indicator in command_indicators):
            return "command"

        # Compliment detection
        compliment_indicators = [
            "good",
            "great",
            "awesome",
            "amazing",
            "fantastic",
            "wonderful",
            "excellent",
            "perfect",
            "nice",
            "cool",
            "sweet",
            "brilliant",
            "outstanding",
            "superb",
            "magnificent",
            "love",
            "like",
            "appreciate",
            "thank",
            "thanks",
            "well done",
            "good job",
            "impressive",
            "you're good",
            "you're great",
            "you're awesome",
            "working well",
            "love you",
        ]

        if any(indicator in content_lower for indicator in compliment_indicators):
            return "compliment"

        # Question detection (more specific)
        question_words = ["what", "how", "why", "where", "who", "which", "whose"]
        question_patterns = [
            "can you",
            "do you",
            "are you",
            "will you",
            "would you",
            "could you",
        ]

        if (
            content_lower.strip().endswith("?")
            or any(word in content_lower for word in question_words)
            or any(pattern in content_lower for pattern in question_patterns)
        ):
            return "question"

        # Greeting detection
        greeting_indicators = [
            "hello",
            "hi",
            "hey",
            "sup",
            "yo",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
            "what's up",
            "whats up",
            "how are you",
            "hows it going",
        ]

        if any(indicator in content_lower for indicator in greeting_indicators):
            return "greeting"

        # Casual conversation
        casual_indicators = [
            "lol",
            "lmao",
            "haha",
            "funny",
            "joke",
            "just saying",
            "by the way",
            "btw",
            "anyway",
            "whatever",
            "maybe",
            "perhaps",
            "i think",
            "in my opinion",
        ]

        if any(indicator in content_lower for indicator in casual_indicators):
            return "casual"

        # Code/tech specific (admin context)
        code_indicators = [
            "code",
            "coding",
            "program",
            "script",
            "function",
            "variable",
            "debug",
            "compile",
            "syntax",
            "logic",
            "algorithm",
            "database",
            "server",
            "client",
            "api",
            "framework",
            "library",
            "repository",
            "commit",
            "push",
            "pull",
            "merge",
            "deploy",
            "production",
        ]

        if any(indicator in content_lower for indicator in code_indicators):
            return "code_talk"

        # Default fallback
        return "general"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle @ mentions to the bot."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Ignore @everyone/@here mentions
        if message.mention_everyone:
            return

        # Check if bot is specifically mentioned
        if not any(mention.id == self.bot.user.id for mention in message.mentions):
            return

        # Don't respond to commands (they start with !)
        if message.content.strip().startswith("!"):
            return

        try:
            # Clean the message content (remove mentions)
            content = message.content
            for mention in message.mentions:
                content = content.replace(f"<@{mention.id}>", "").replace(
                    f"<@!{mention.id}>", ""
                )
            content = content.strip().lower()

            logger.info(f"Bot mentioned by {message.author} with: '{content}'")

            # Analyze message intent first
            intent = self._analyze_message_intent(content)
            logger.info(f"Message intent detected: {intent}")

            # Handle time-related queries (highest priority)
            if intent == "time_query":
                await self._handle_time_query(message, content)
                return

            # Handle other intents with contextual responses
            response = self._get_intent_based_response(
                intent, content, message.author.id
            )

            # Add random emoji for flavor
            emojis = ["😏", "🤖", "💀", "😎", "🙄", "😂", "🤷‍♀️", "💅", "🔥", "✨"]
            if not any(emoji in response for emoji in emojis):
                response += f" {random.choice(emojis)}"

            await message.reply(response)

        except Exception as e:
            logger.error(f"Error handling mention: {e}")
            # Even error responses should be sassy
            await message.reply("I broke trying to read your message. Thanks. 💀")

    async def _handle_time_query(self, message, content):
        """
        Handle time-related queries about events.

        Args:
            message: Discord message object
            content: Cleaned message content

        Provides:
        - Event schedule information
        - Time until next event
        - Team-specific timings
        - Current signup counts
        """
        try:
            # Get event manager to check current times
            event_manager = self.bot.get_cog("EventManager")
            if not event_manager:
                await message.reply(
                    "Event system is down! Probably your fault though 🤷‍♀️"
                )
                return

            # Parse which team they're asking about
            target_team = None
            if any(
                phrase in content
                for phrase in ["team 2", "team2", "team_2", "second team"]
            ):
                target_team = "team_2"
            elif any(
                phrase in content
                for phrase in ["team 3", "team3", "team_3", "third team"]
            ):
                target_team = "team_3"
            elif any(
                phrase in content
                for phrase in [
                    "main",
                    "team 1",
                    "team1",
                    "team_1",
                    "first team",
                    "main team",
                ]
            ):
                target_team = "main_team"

            # Get current times
            event_times = event_manager.event_times or DEFAULT_TIMES

            if target_team:
                # Specific team query
                team_time_str = event_times.get(target_team, "TBD")
                team_display = TEAM_DISPLAY.get(
                    target_team, target_team.replace("_", " ").title()
                )

                time_until = self._calculate_time_until_event(team_time_str)

                response = f"**{team_display}** is at `{team_time_str}`"
                if time_until:
                    response += f"\n{time_until}"
                else:
                    response += "\n(I couldn't figure out when that actually is, blame the programmer 🤷‍♀️)"

            else:
                # General "when is next row" query
                embed = discord.Embed(
                    title="📅 Next RoW Event Times",
                    description="Here's when each team plays:",
                    color=0x5865F2,
                )

                for team_key, team_name in TEAM_DISPLAY.items():
                    team_time_str = event_times.get(team_key, "TBD")
                    time_until = self._calculate_time_until_event(team_time_str)

                    value = f"**Time:** {team_time_str}"
                    if time_until:
                        value += f"\n**{time_until}**"

                    embed.add_field(name=team_name, value=value, inline=True)

                # Add current team signups
                total_signups = sum(
                    len(members) for members in event_manager.events.values()
                )
                embed.set_footer(
                    text=f"Current signups: {total_signups} players • Asked by {message.author.display_name}"
                )

                await message.reply(embed=embed)
                return

            await message.reply(response)

        except Exception as e:
            logger.error(f"Error handling time query: {e}")
            await message.reply("I broke trying to calculate time. Math is hard! 🤯")

    def _calculate_time_until_event(self, time_str):
        """
        Calculate time until event from string.

        Args:
            time_str: Time string in format '14:00 UTC Saturday'

        Returns:
            str: Formatted time difference or None if invalid

        Examples:
            "5 days, 3 hours from now"
            "2 hours, 30 minutes from now"
        """
        try:
            # Parse time string
            parts = time_str.split()
            if len(parts) < 3:
                return None

            time_part = parts[0]  # "14:00"
            day_part = parts[2]  # "Saturday"

            hour, minute = map(int, time_part.split(":"))

            # Map day names to weekday numbers
            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }

            target_day = day_map.get(day_part.lower())
            if target_day is None:
                return None

            # Calculate next occurrence
            now = datetime.utcnow()
            days_ahead = target_day - now.weekday()

            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7

            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            target_time += timedelta(days=days_ahead)

            # Calculate difference
            time_diff = target_time - now

            if time_diff.total_seconds() < 0:
                return None

            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60

            # Format response
            if days > 0:
                return f"⏰ **{days} days, {hours} hours** from now"
            elif hours > 0:
                return f"⏰ **{hours} hours, {minutes} minutes** from now"
            else:
                return f"⏰ **{minutes} minutes** from now"

        except Exception as e:
            logger.error(f"Error calculating time until event: {e}")
            return None

    def _get_intent_based_response(self, intent, content, user_id):
        """
        Get appropriate response based on intent and user authority.

        Args:
            intent: Detected message intent
            content: Message content
            user_id: Discord user ID

        Returns:
            str: Selected response based on intent and user type

        Features:
        - Different responses for admins vs regular users
        - Intent-specific response selection
        - Random emoji additions
        """
        from config.settings import BOT_ADMIN_USER_ID

        is_admin = user_id == BOT_ADMIN_USER_ID

        # Add more dynamic response selection
        if intent == "command":
            responses = (
                self.admin_command_responses
                if is_admin
                else self.user_command_responses
            )
            return random.choice(responses)

        elif intent == "code_talk":
            responses = (
                self.admin_tech_responses if is_admin else self.user_tech_responses
            )
            return random.choice(responses)

        elif intent == "casual":
            responses = (
                self.admin_casual_responses
                if is_admin
                else self.peasant_greeting_responses
            )
            return random.choice(responses)

        elif intent == "complaint":
            if is_admin:
                return random.choice(self.admin_sassy_responses)
            else:
                return random.choice(self.peasant_sassy_responses)

        elif intent == "compliment":
            if is_admin:
                return random.choice(self.admin_compliment_responses)
            else:
                return random.choice(self.peasant_compliment_responses)

        elif intent == "greeting":
            if is_admin:
                return random.choice(self.admin_greeting_responses)
            else:
                return random.choice(self.peasant_greeting_responses)

        else:  # general/fallback
            if is_admin:
                return random.choice(
                    [
                        "I have no idea what you just said, but you're my creator so... okay! 🤷‍♀️",
                        "Interesting input, boss! Still processing... 🤖",
                        "That's nice, daddy 💅",
                        "Cool story, creator! 📖",
                        "Beep boop, parent detected 🤖",
                        "I'm pretending to understand what my maker means 🎭",
                        "Fascinating! Your code, however... 💫",
                        "Classic creator behavior right there 🎯",
                    ]
                )
            else:
                return random.choice(
                    [
                        "I have no idea what you just said, and I don't care! 🤷‍♀️",
                        "Interesting... anyway... 💫",
                        "That's nice, random person 💅",
                        "Cool story, nobody! 📖",
                        "Beep boop, irrelevant human detected 🤖",
                        "I'm pretending to care about your opinion 🎭",
                        "Fascinating! Now go bother someone else 💫",
                        "That sounds like a 'not my problem' situation 🤔",
                    ]
                )

    @commands.command(name="sassy", help="Test the bot's sass levels")
    async def test_sass(self, ctx):
        """Test command to see bot's attitude."""
        responses = [
            "My sass levels are MAXIMUM today! 📈💅",
            "You want sass? I AM sass! ✨",
            "Buckle up buttercup, I'm feeling spicy today! 🌶️",
            "Sass level: Definitely higher than your coding skills 📊",
            "I'm not sassy, I'm just brutally honest! 😏",
            "Testing sass... ERROR: Too much sass detected! 🚨",
        ]
        await ctx.send(random.choice(responses))


async def setup(bot):
    """
    Set up the MentionHandler cog.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(MentionHandler(bot))
