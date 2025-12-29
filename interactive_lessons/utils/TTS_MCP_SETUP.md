# Text-to-Speech (TTS) MCP Server Setup Guide

This guide explains how to use the blacktop/mcp-tts server for adding text-to-speech capabilities to Claude Code.

## What is mcp-tts?

The mcp-tts server is a Model Context Protocol server that provides multiple text-to-speech services. It allows Claude Code to convert text into spoken audio using various TTS engines.

## Installation Status

✅ **Go Language** - Installed (version 1.25.4)
✅ **mcp-tts** - Installed at `/Users/morgan/go/bin/mcp-tts`
✅ **Claude Desktop** - Configured with TTS server

## Available TTS Services

The mcp-tts server provides **four different TTS services**:

### 1. say_tts (macOS Built-in) ✅ READY
- **Requirements:** None (uses macOS system voices)
- **Voices:** All macOS system voices
- **Cost:** Free
- **Quality:** Good
- **Best for:** Quick testing, offline use

### 2. elevenlabs_tts (Premium AI)
- **Requirements:** `ELEVENLABS_API_KEY`
- **Voices:** Premium AI voices with natural emotion
- **Cost:** Paid (subscription required)
- **Quality:** Excellent
- **Best for:** High-quality narration, professional content

### 3. google_tts (Google Gemini)
- **Requirements:** `GOOGLE_AI_API_KEY` or `GEMINI_API_KEY`
- **Voices:** 30+ voices (Zephyr, Puck, Charon, etc.)
- **Cost:** Paid (per-character pricing)
- **Quality:** Very good
- **Best for:** Multiple language support, natural voices

### 4. openai_tts (OpenAI)
- **Requirements:** `OPENAI_API_KEY`
- **Voices:** 10 natural voices, 3 quality tiers
- **Cost:** Paid (per-character pricing)
- **Quality:** Very good to excellent
- **Best for:** Variety of voices, speed control (0.25x-4.0x)

## Current Configuration

### Basic Setup (macOS say only)

Your current configuration uses **say_tts only** (no API keys required):

```json
{
  "mcpServers": {
    "tts-server": {
      "command": "/Users/morgan/go/bin/mcp-tts",
      "env": {
        "MCP_TTS_SUPPRESS_SPEAKING_OUTPUT": "false",
        "MCP_TTS_ALLOW_CONCURRENT": "false"
      }
    }
  }
}
```

This gives you immediate access to macOS system voices at no cost!

### Adding Cloud TTS Services (Optional)

To enable ElevenLabs, Google, or OpenAI TTS, update the config:

```json
{
  "mcpServers": {
    "tts-server": {
      "command": "/Users/morgan/go/bin/mcp-tts",
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "ELEVENLABS_API_KEY": "your-elevenlabs-key-here",
        "ELEVENLABS_VOICE_ID": "1SM7GgM6IMuvQlz2BwM3",
        "GOOGLE_AI_API_KEY": "your-google-key-here",
        "OPENAI_TTS_INSTRUCTIONS": "Speak in a cheerful and positive tone",
        "MCP_TTS_SUPPRESS_SPEAKING_OUTPUT": "false",
        "MCP_TTS_ALLOW_CONCURRENT": "false"
      }
    }
  }
}
```

## How to Use

After restarting Claude Desktop, you can ask me to speak text:

### Example Requests:

**Basic Text-to-Speech:**
```
"Read this aloud: The Pythagorean theorem states that a² + b² = c²"
"Speak the following explanation..."
"Use text-to-speech to say: Welcome to LCAI Maths"
```

**For Educational Content:**
```
"Read aloud the steps to solve this equation"
"Speak the explanation of derivatives with a teaching tone"
"Convert this lesson summary to audio"
```

**Voice Selection (macOS):**
```
"Use the Alex voice to read this"
"Speak with the Samantha voice"
"Read this using the Daniel voice"
```

**Speed Control (OpenAI):**
```
"Read this slowly (0.5x speed)"
"Speak this at 1.5x speed"
```

## Configuration Options

### Sequential Mode (Default)
- Only one TTS request plays at a time
- Prevents overlapping speech
- Uses system-wide file lock
- Set `MCP_TTS_ALLOW_CONCURRENT=false`

### Concurrent Mode
- Multiple TTS requests can play simultaneously
- May create overlapping audio
- Set `MCP_TTS_ALLOW_CONCURRENT=true`

### Output Suppression
- `false`: Shows "Speaking: [text]" messages (current setting)
- `true`: Shows "Speech completed" instead
- Set via `MCP_TTS_SUPPRESS_SPEAKING_OUTPUT`

## Use Cases for LCAI Maths

### 1. Audio Explanations
Generate audio explanations of mathematical concepts:
```
"Create an audio explanation of how to use the quadratic formula"
"Read aloud the steps to solve this trigonometry problem"
```

### 2. Accessibility
Make content accessible to students with visual impairments:
```
"Convert this lesson into audio format"
"Read the question text aloud"
```

### 3. Study Aids
Create audio study materials:
```
"Read these formula definitions for audio flashcards"
"Speak the key points from this lesson summary"
```

### 4. Multi-modal Learning
Combine visual and audio learning:
```
"Show the diagram and read the explanation aloud"
"Display the formula and speak how to use it"
```

## Available macOS Voices

To see all available system voices, run:
```bash
say -v ?
```

Common voices include:
- **Alex** - Default male voice
- **Samantha** - Female voice
- **Daniel** - British male voice
- **Karen** - Australian female voice
- **Victoria** - Female voice
- **Fred** - Novelty voice (old-style Mac)

## Cost Comparison

| Service | Cost | API Key Required | Quality | Best Use Case |
|---------|------|------------------|---------|---------------|
| **say_tts** | Free | No | Good | Testing, offline |
| **ElevenLabs** | $5-$99/mo | Yes | Excellent | Professional content |
| **Google TTS** | ~$4/million chars | Yes | Very Good | Multi-language |
| **OpenAI TTS** | $15/million chars | Yes | Very Good | Speed control |

## Troubleshooting

### TTS Server Not Available

1. **Check configuration:**
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Verify mcp-tts installation:**
   ```bash
   /Users/morgan/go/bin/mcp-tts --help
   ```

3. **Restart Claude Desktop completely**

### No Audio Playing

1. **Check system volume**
2. **Verify speakers/headphones connected**
3. **Test macOS say directly:**
   ```bash
   say "Hello, this is a test"
   ```

### API Key Errors

If using cloud services:
1. Verify API keys are correct
2. Check API key permissions
3. Ensure you have billing/credits enabled

## Integration with Django

While TTS runs through Claude Code (not directly in Django), you can:

1. **Generate audio files:**
   - Ask Claude Code to create TTS audio
   - Save output to Django media folder
   - Link audio files to questions/lessons

2. **Create audio resources:**
   - Generate pronunciation guides
   - Create audio hints
   - Build audio answer explanations

## Next Steps

### Immediate Use (No API Keys)
**Ready now!** Just restart Claude Desktop and start using macOS voices:
```
"Use text-to-speech to read: The derivative of x² is 2x"
```

### Optional: Add Cloud Services
If you want premium voices:
1. Get API keys from OpenAI, ElevenLabs, or Google
2. Update the configuration file
3. Restart Claude Desktop
4. Enjoy higher quality voices!

## Summary

✅ **TTS Server Installed and Configured**
✅ **macOS Voices Ready** (no API keys needed)
✅ **Four TTS Services Available** (one free, three paid)
✅ **Sequential Mode Enabled** (prevents overlap)

**Ready to use after restarting Claude Desktop!**

Simply ask me to "speak" or "read aloud" any text, and I'll use the TTS server to convert it to audio.

## Resources

- **GitHub Repository:** https://github.com/blacktop/mcp-tts
- **MCP Documentation:** https://modelcontextprotocol.io/
- **OpenAI TTS Pricing:** https://openai.com/pricing#audio-models
- **ElevenLabs Pricing:** https://elevenlabs.io/pricing
- **Google Cloud TTS:** https://cloud.google.com/text-to-speech/pricing
