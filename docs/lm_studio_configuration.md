# LM Studio Configuration Guide

This guide helps you configure LM Studio to work properly with the sync system, particularly for handling large context windows.

## Quick Status Check

Run this command to quickly check your LM Studio configuration:

```bash
python check_lm_studio.py
```

This will show you:
- ✅/❌ Server status
- ✅/❌ Model loading status  
- ✅/❌ Context length status

## Configuration Tools

### 1. Quick Status Check
```bash
python check_lm_studio.py
```

### 2. Configuration Guide
```bash
python check_lm_studio.py fix
```

### 3. Test Context Length
```bash
python check_lm_studio.py test
```

### 4. Detailed Diagnostic
```bash
python check_lm_studio.py status
```

### 5. Interactive Helper
```bash
python src/sync/utils/lm_studio_config_helper.py interactive
```

## Manual Configuration Steps

If the quick check shows context length issues, follow these steps:

### Step 1: Open LM Studio
1. Launch LM Studio from your Applications folder
2. Wait for the application to fully load

### Step 2: Load Model with Correct Context Length
1. Go to the **"My Models"** tab
2. Find the **"qwen2-vl-7b-instruct"** model
3. Click the **gear icon (⚙️)** next to the model
4. Set **"Context Length"** to **32768** (32K)
5. Click **"Load"** button

### Step 3: Verify Configuration
1. Wait for the model to load completely
2. Check that the model shows as **"Loaded"**
3. Run the status check again to verify

### Step 4: Keep Model Loaded
- Once configured, keep the model loaded
- Don't close LM Studio during processing
- The model will remain available for API calls

## Troubleshooting

### Context Length Still Too Small
If you can't set the context length to 32K:

1. **Try a different model variant** that supports larger context
2. **Use smaller context windows** and process text in chunks
3. **Check LM Studio version** - newer versions may support larger context

### Model Won't Load
1. **Check available memory** - large context requires more RAM
2. **Try a smaller model** or different quantization
3. **Restart LM Studio** and try again

### Server Not Responding
1. **Check if LM Studio is running**
2. **Verify port 1234** is not blocked
3. **Restart LM Studio** application

## Technical Details

### Required Configuration
- **Model**: qwen2-vl-7b-instruct
- **Context Length**: 32,768 tokens (32K)
- **Server Port**: 1234
- **API Endpoint**: http://localhost:1234/v1

### Why 32K Context?
The sync system processes large documents that require substantial context windows. The 32K context length ensures that:
- Large documents can be processed in fewer chunks
- Better understanding of document context
- More accurate information extraction

### Current Limitations
- LM Studio doesn't provide programmatic server configuration
- Context length must be set manually in the UI
- Model must remain loaded during processing

## Integration with Sync System

The sync system automatically:
- Detects LM Studio configuration issues
- Provides helpful error messages
- Guides users through configuration
- Tests context length before processing

### Error Messages
If you see context overflow errors:
```
"However, the model is loaded with context length of only 4096 tokens, which is not enough"
```

This means you need to configure LM Studio with a larger context length as described above.

## Support

If you continue to have issues:
1. Run the diagnostic tools to get detailed information
2. Check LM Studio documentation
3. Ensure you have sufficient system resources
4. Consider using a different model or processing approach 