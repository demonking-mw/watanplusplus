import React, { useContext, useState, useEffect } from "react";
import {
  Drawer,
  Typography,
  IconButton,
  Divider,
  Paper,
  TextField,
  Button,
  Box,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import SaveIcon from "@mui/icons-material/Save";
import CancelIcon from "@mui/icons-material/Cancel";
import { store } from "../store";
import ACTIONS from "../actions";
import { playerKey } from "../utils/stateUtils";
import type { Color, ResourceCard } from "../utils/api.types";
import { API_URL } from "../configuration";
import { useParams } from "react-router-dom";
import axios from "axios";
import { getState } from "../utils/apiClient";
import "./ResourceEditor.scss";

type ResourceEditorProps = {
  open: boolean;
  onClose: () => void;
  anchor?: "left" | "right" | "top" | "bottom";
};

const RESOURCES: ResourceCard[] = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"];

type ResourceChanges = {
  [color: string]: {
    [resource: string]: number;
  };
};

export default function ResourceEditor({
  open,
  onClose,
  anchor = "right",
}: ResourceEditorProps) {
  const { state, dispatch } = useContext(store);
  const { gameId } = useParams();
  const { gameState } = state;

  // Track pending changes
  const [pendingChanges, setPendingChanges] = useState<ResourceChanges>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Reset changes when drawer opens/closes or game state changes
  useEffect(() => {
    if (open && gameState) {
      setPendingChanges({});
      setHasChanges(false);
    }
  }, [open, gameState]);

  if (!gameState) {
    return null;
  }

  const getCurrentValue = (color: Color, resource: ResourceCard): number => {
    const key = playerKey(gameState, color);
    const originalAmount = (gameState.player_state[`${key}_${resource}_IN_HAND`] as number) || 0;
    
    // Check if there's a pending change
    if (pendingChanges[color] && pendingChanges[color][resource] !== undefined) {
      return pendingChanges[color][resource];
    }
    
    return originalAmount;
  };

  const handleResourceChange = (
    color: Color,
    resource: ResourceCard,
    delta: number
  ) => {
    const currentValue = getCurrentValue(color, resource);
    const newValue = Math.max(0, currentValue + delta);
    
    setPendingChanges((prev) => ({
      ...prev,
      [color]: {
        ...(prev[color] || {}),
        [resource]: newValue,
      },
    }));
    setHasChanges(true);
  };

  const handleDirectInput = (
    color: Color,
    resource: ResourceCard,
    value: string
  ) => {
    // If empty, don't update (user is still typing)
    if (value === "") {
      return;
    }
    
    const numValue = parseInt(value, 10);
    if (isNaN(numValue) || numValue < 0) {
      return;
    }
    
    setPendingChanges((prev) => ({
      ...prev,
      [color]: {
        ...(prev[color] || {}),
        [resource]: numValue,
      },
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!gameId || !hasChanges) return;

    try {
      // Send all changes as a batch
      const response = await axios.post<typeof gameState>(
        `${API_URL}/api/games/${gameId}/resources/batch`,
        {
          changes: Object.entries(pendingChanges).flatMap(([color, resources]) =>
            Object.entries(resources).map(([resource, amount]) => ({
              color,
              resource,
              amount,
            }))
          ),
        }
      );

      // Update the game state in the store
      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      
      // Reset changes
      setPendingChanges({});
      setHasChanges(false);
    } catch (error) {
      console.error("Error saving resources:", error);
    }
  };

  const handleCancel = () => {
    setPendingChanges({});
    setHasChanges(false);
  };

  return (
    <Drawer 
      anchor={anchor} 
      open={open} 
      onClose={onClose} 
      className="resource-editor"
      variant="temporary" // Temporary so it overlays other drawers
    >
      <div className="resource-editor-content">
        <Box className="editor-header">
          <Typography variant="h6" className="editor-title">
            Resource Editor
          </Typography>
          {hasChanges && (
            <Box className="editor-actions">
              <Button
                variant="outlined"
                size="small"
                onClick={handleCancel}
                startIcon={<CancelIcon />}
                className="cancel-btn"
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                size="small"
                onClick={handleSave}
                startIcon={<SaveIcon />}
                className="save-btn"
              >
                Save
              </Button>
            </Box>
          )}
        </Box>
        <Divider />
        {gameState.colors.map((color) => {
          const key = playerKey(gameState, color);
          const isCurrentPlayer = color === gameState.current_color;
          return (
            <Paper
              key={color}
              className={`player-editor-section ${color.toLowerCase()} ${
                isCurrentPlayer ? "current-player" : ""
              }`}
              elevation={2}
            >
              <Typography variant="subtitle1" className="player-name">
                {color} {isCurrentPlayer && "← Current"}
              </Typography>
              <Divider style={{ margin: "8px 0" }} />
              {RESOURCES.map((resource) => {
                const amount = getCurrentValue(color, resource);
                const hasPendingChange = pendingChanges[color] && pendingChanges[color][resource] !== undefined;
                return (
                  <div key={resource} className="resource-control">
                    <Typography variant="body2" className="resource-label">
                      {resource}
                    </Typography>
                    <div className="resource-input-group">
                      <IconButton
                        size="small"
                        onClick={() => handleResourceChange(color, resource, -1)}
                        disabled={amount <= 0}
                        className="minus-btn"
                      >
                        <RemoveIcon />
                      </IconButton>
                      <TextField
                        type="number"
                        value={amount}
                        onChange={(e) => handleDirectInput(color, resource, e.target.value)}
                        inputProps={{
                          min: 0,
                          style: { textAlign: "center", padding: "4px 8px" },
                        }}
                        size="small"
                        className={`resource-input ${hasPendingChange ? "has-change" : ""}`}
                        variant="outlined"
                      />
                      <IconButton
                        size="small"
                        onClick={() => handleResourceChange(color, resource, 1)}
                        className="plus-btn"
                      >
                        <AddIcon />
                      </IconButton>
                    </div>
                  </div>
                );
              })}
            </Paper>
          );
        })}
      </div>
    </Drawer>
  );
}
