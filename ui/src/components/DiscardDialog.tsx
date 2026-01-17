import React, { useContext, useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import { store } from "../store";
import ACTIONS from "../actions";
import { playerKey } from "../utils/stateUtils";
import type { ResourceCard, GameAction } from "../utils/api.types";
import { postAction } from "../utils/apiClient";
import { useParams } from "react-router-dom";
import { getHumanColor } from "../utils/stateUtils";
import "./DiscardDialog.scss";

type DiscardDialogProps = {
  open: boolean;
  onClose: () => void;
};

const RESOURCES: ResourceCard[] = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"];

export default function DiscardDialog({
  open,
  onClose,
}: DiscardDialogProps) {
  const { state, dispatch } = useContext(store);
  const { gameId } = useParams();
  const { gameState } = state;

  const [selectedDiscards, setSelectedDiscards] = useState<{
    [key in ResourceCard]: number;
  }>({
    WOOD: 0,
    BRICK: 0,
    SHEEP: 0,
    WHEAT: 0,
    ORE: 0,
  });

  // Calculate how many cards player has and needs to discard
  const discardInfo = useMemo(() => {
    if (!gameState) return { totalCards: 0, numToDiscard: 0, playerResources: {} };
    
    const currentPlayerColor = gameState.current_color;
    const key = playerKey(gameState, currentPlayerColor);
    
    const playerResources: { [key in ResourceCard]: number } = {
      WOOD: gameState.player_state[`${key}_WOOD_IN_HAND`] || 0,
      BRICK: gameState.player_state[`${key}_BRICK_IN_HAND`] || 0,
      SHEEP: gameState.player_state[`${key}_SHEEP_IN_HAND`] || 0,
      WHEAT: gameState.player_state[`${key}_WHEAT_IN_HAND`] || 0,
      ORE: gameState.player_state[`${key}_ORE_IN_HAND`] || 0,
    };
    
    const totalCards = Object.values(playerResources).reduce((sum, count) => sum + count, 0);
    const numToDiscard = Math.floor(totalCards / 2);
    
    return { totalCards, numToDiscard, playerResources };
  }, [gameState]);

  // Reset selections when dialog opens
  useEffect(() => {
    if (open) {
      setSelectedDiscards({
        WOOD: 0,
        BRICK: 0,
        SHEEP: 0,
        WHEAT: 0,
        ORE: 0,
      });
    }
  }, [open]);

  if (!gameState) return null;

  const currentPlayerColor = gameState.current_color;
  const humanColor = getHumanColor(gameState);
  const totalSelected = Object.values(selectedDiscards).reduce((sum, count) => sum + count, 0);
  const canDiscard = totalSelected === discardInfo.numToDiscard;

  const handleResourceChange = (resource: ResourceCard, delta: number) => {
    setSelectedDiscards((prev) => {
      const current = prev[resource];
      const maxAvailable = discardInfo.playerResources[resource] || 0;
      const newValue = Math.max(0, Math.min(maxAvailable, current + delta));
      return { ...prev, [resource]: newValue };
    });
  };

  const handleDiscard = async () => {
    if (!gameId || !canDiscard) return;

    // Ensure we're using the current player from gameState (not stale)
    const playerToDiscard = gameState.current_color;
    
    // Build list of resources to discard
    const resourcesToDiscard: ResourceCard[] = [];
    for (const resource of RESOURCES) {
      for (let i = 0; i < selectedDiscards[resource]; i++) {
        resourcesToDiscard.push(resource);
      }
    }

    console.log(`Discarding ${resourcesToDiscard.length} cards for player: ${playerToDiscard}`, resourcesToDiscard);
    const action: GameAction = [playerToDiscard, "DISCARD", resourcesToDiscard];
    const updatedGameState = await postAction(gameId, action);
    dispatch({ type: ACTIONS.SET_GAME_STATE, data: updatedGameState });
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      className="discard-dialog"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Discard Cards - {currentPlayerColor}</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ mb: 2, color: "white" }}>
          <strong>{currentPlayerColor}</strong> has {discardInfo.totalCards} cards and must discard {discardInfo.numToDiscard} cards.
        </Typography>
        <Typography variant="body2" sx={{ mb: 2, color: totalSelected === discardInfo.numToDiscard ? "green" : "orange" }}>
          Selected: {totalSelected} / {discardInfo.numToDiscard}
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {RESOURCES.map((resource) => {
            const available = discardInfo.playerResources[resource] || 0;
            const selected = selectedDiscards[resource];
            const canIncrease = selected < available && totalSelected < discardInfo.numToDiscard;
            const canDecrease = selected > 0;

            return (
              <Box
                key={resource}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  p: 1.5,
                  bgcolor: "rgba(255, 255, 255, 0.1)",
                  borderRadius: 1,
                }}
              >
                <Typography variant="body1" sx={{ color: "white", minWidth: 80 }}>
                  {resource}
                </Typography>
                <Typography variant="body2" sx={{ color: "rgba(255, 255, 255, 0.7)", mr: 2 }}>
                  (You have: {available})
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <IconButton
                    size="small"
                    onClick={() => handleResourceChange(resource, -1)}
                    disabled={!canDecrease}
                    sx={{ color: "white" }}
                  >
                    <RemoveIcon />
                  </IconButton>
                  <Typography
                    variant="h6"
                    sx={{
                      minWidth: 40,
                      textAlign: "center",
                      color: "white",
                    }}
                  >
                    {selected}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => handleResourceChange(resource, 1)}
                    disabled={!canIncrease}
                    sx={{ color: "white" }}
                  >
                    <AddIcon />
                  </IconButton>
                </Box>
              </Box>
            );
          })}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="secondary">
          Cancel
        </Button>
        <Button
          onClick={handleDiscard}
          variant="contained"
          disabled={!canDiscard}
          color="primary"
        >
          Discard {totalSelected} Cards
        </Button>
      </DialogActions>
    </Dialog>
  );
}
