import pytest
from discord.ext.commands import Context
from unittest.mock import AsyncMock, MagicMock
from commands.vowelize import vowelize


@pytest.mark.asyncio
async def test_vowelize_command():
    """Test the vowelize command with a simple Hebrew word"""
    # Mock Discord context
    ctx = MagicMock(spec=Context)
    ctx.send = AsyncMock()
    
    # Create a mock for the processing message
    processing_msg = MagicMock()
    processing_msg.delete = AsyncMock()
    ctx.send.return_value = processing_msg
    
    # Test the vowelize command
    await vowelize(ctx, text="שלום")
    
    # Verify the processing message was sent and deleted
    ctx.send.assert_any_call("Processing your text... 🔄")
    processing_msg.delete.assert_called_once()
    
    # Verify that some response was sent
    # The last call should be the actual response
    assert ctx.send.call_count >= 2
    last_call_args = ctx.send.call_args_list[-1][0][0]
    assert "Vowelized text:" in last_call_args
    assert "Word Analysis:" in last_call_args
