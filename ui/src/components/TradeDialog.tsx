import React, { useState, useContext } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Tabs,
  Tab,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Paper,
} from "@mui/material";
import { store } from "../store";
import { playerKey } from "../utils/stateUtils";
import type { Color, ResourceCard } from "../utils/api.types";
import { API_URL } from "../configuration";
import { useParams } from "react-router-dom";
import axios from "axios";
import ACTIONS from "../actions";
import "./TradeDialog.scss";

type TradeDialogProps = {
  open: boolean;
  onClose: () => void;
};

const RESOURCES: ResourceCard[] = ["WOOD", "BRICK", "SHEEP", "WHEAT", "ORE"];

type ResourceCounts = {
  [key in ResourceCard]: number;
};

export default function TradeDialog({ open, onClose }: TradeDialogProps) {
  const { state, dispatch } = useContext(store);
  const { gameId } = useParams();
  const { gameState } = state;

  const [tabValue, setTabValue] = useState(0);
  
  // Bank trade state
  const [bankGiveResource, setBankGiveResource] = useState<ResourceCard>("WOOD");
  const [bankGiveAmount, setBankGiveAmount] = useState(4);
  const [bankReceiveResource, setBankReceiveResource] = useState<ResourceCard>("BRICK");
  
  // Player trade state
  const [selectedPlayer, setSelectedPlayer] = useState<Color | null>(null);
  const [playerGiveResources, setPlayerGiveResources] = useState<ResourceCounts>({
    WOOD: 0,
    BRICK: 0,
    SHEEP: 0,
    WHEAT: 0,
    ORE: 0,
  });
  const [playerReceiveResources, setPlayerReceiveResources] = useState<ResourceCounts>({
    WOOD: 0,
    BRICK: 0,
    SHEEP: 0,
    WHEAT: 0,
    ORE: 0,
  });

  if (!gameState) {
    return null;
  }

  const currentPlayerColor = gameState.current_color;
  const currentPlayerKey = playerKey(gameState, currentPlayerColor);
  
  const getPlayerResourceCount = (color: Color, resource: ResourceCard): number => {
    const key = playerKey(gameState!, color);
    return (gameState!.player_state[`${key}_${resource}_IN_HAND`] as number) || 0;
  };

  const handleBankTrade = async () => {
    if (!gameId) return;

    // Create maritime trade action: 5-tuple where first 4 are giving resources, last is receiving
    const tradeValue: (ResourceCard | null)[] = [];
    for (let i = 0; i < bankGiveAmount; i++) {
      tradeValue.push(bankGiveResource);
    }
    // Fill remaining slots with null (for port trades, this would be handled differently)
    while (tradeValue.length < 4) {
      tradeValue.push(null);
    }
    tradeValue.push(bankReceiveResource);

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "MARITIME_TRADE", tradeValue]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      
      // Reset bank trade form
      setBankGiveResource("WOOD");
      setBankGiveAmount(4);
      setBankReceiveResource("BRICK");
      
      onClose();
    } catch (error) {
      console.error("Error executing bank trade:", error);
    }
  };

  const handleOfferPlayerTrade = async () => {
    if (!gameId || !selectedPlayer) return;

    // Create CONFIRM_TRADE action directly: 11-tuple (first 10 are trade, last is accepting player)
    // This automatically completes the trade without waiting for acceptance
    const tradeValue = [
      playerGiveResources.WOOD,
      playerGiveResources.BRICK,
      playerGiveResources.SHEEP,
      playerGiveResources.WHEAT,
      playerGiveResources.ORE,
      playerReceiveResources.WOOD,
      playerReceiveResources.BRICK,
      playerReceiveResources.SHEEP,
      playerReceiveResources.WHEAT,
      playerReceiveResources.ORE,
      selectedPlayer, // The player we're trading with
    ];

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "CONFIRM_TRADE", tradeValue]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      
      // Reset player trade form
      setPlayerGiveResources({
        WOOD: 0,
        BRICK: 0,
        SHEEP: 0,
        WHEAT: 0,
        ORE: 0,
      });
      setPlayerReceiveResources({
        WOOD: 0,
        BRICK: 0,
        SHEEP: 0,
        WHEAT: 0,
        ORE: 0,
      });
      setSelectedPlayer(null);
      
      onClose();
    } catch (error) {
      console.error("Error executing player trade:", error);
    }
  };

  const handleAcceptTrade = async () => {
    if (!gameId || !currentTrade) return;

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "ACCEPT_TRADE", currentTrade]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      onClose();
    } catch (error) {
      console.error("Error accepting trade:", error);
    }
  };

  const handleRejectTrade = async () => {
    if (!gameId || !currentTrade) return;

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "REJECT_TRADE", currentTrade]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      onClose();
    } catch (error) {
      console.error("Error rejecting trade:", error);
    }
  };

  const handleConfirmTrade = async (acceptingPlayerColor: Color) => {
    if (!gameId || !currentTrade) return;

    // CONFIRM_TRADE: 11-tuple (first 10 as OFFER_TRADE, last is accepting player color)
    const tradeValue = [...currentTrade.slice(0, 10), acceptingPlayerColor];

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "CONFIRM_TRADE", tradeValue]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      onClose();
    } catch (error) {
      console.error("Error confirming trade:", error);
    }
  };

  const handleCancelTrade = async () => {
    if (!gameId) return;

    try {
      const response = await axios.post(
        `${API_URL}/api/games/${gameId}/actions`,
        [currentPlayerColor, "CANCEL_TRADE", null]
      );

      dispatch({ type: ACTIONS.SET_GAME_STATE, data: response.data });
      onClose();
    } catch (error) {
      console.error("Error canceling trade:", error);
    }
  };

  // Check if there's a pending trade offer
  const hasPendingTrade = gameState.is_resolving_trade && gameState.current_trade && Array.isArray(gameState.current_trade);
  const currentTrade = hasPendingTrade ? gameState.current_trade : null;
  const isTradeOfferer = hasPendingTrade && currentTrade && currentTrade[10] === gameState.state_index;
  const isTradeDecider = hasPendingTrade && gameState.current_color === currentPlayerColor && !isTradeOfferer;

  // Calculate totals for player trade
  const totalGiving = Object.values(playerGiveResources).reduce((a, b) => a + b, 0);
  const totalReceiving = Object.values(playerReceiveResources).reduce((a, b) => a + b, 0);

  // Check if player has enough resources for bank trade
  const hasEnoughForBankTrade = getPlayerResourceCount(currentPlayerColor, bankGiveResource) >= bankGiveAmount;

  // Check if player has enough resources for player trade
  const hasEnoughForPlayerTrade = RESOURCES.every(
    (resource) => getPlayerResourceCount(currentPlayerColor, resource) >= playerGiveResources[resource]
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth className="trade-dialog">
      <DialogTitle>
        {hasPendingTrade ? (
          isTradeDecider ? (
            "Respond to Trade Offer"
          ) : isTradeOfferer ? (
            "Select Trade Partner"
          ) : (
            "Trade"
          )
        ) : (
          "Trade Resources"
        )}
      </DialogTitle>
      <DialogContent>
        {hasPendingTrade ? (
          // Show pending trade UI
          isTradeDecider ? (
            // Player needs to accept/reject
            <Box className="trade-response">
              <Typography variant="h6">Trade Offer</Typography>
              <Paper className="trade-details">
                <Typography variant="subtitle2">You are giving:</Typography>
                {currentTrade && RESOURCES.map((resource) => {
                  const amount = currentTrade[RESOURCES.indexOf(resource)];
                  if (amount > 0) {
                    return (
                      <Typography key={resource}>
                        {amount}x {resource}
                      </Typography>
                    );
                  }
                  return null;
                })}
                <Divider style={{ margin: "16px 0" }} />
                <Typography variant="subtitle2">You are receiving:</Typography>
                {currentTrade && RESOURCES.map((resource) => {
                  const amount = currentTrade[RESOURCES.indexOf(resource) + 5];
                  if (amount > 0) {
                    return (
                      <Typography key={resource}>
                        {amount}x {resource}
                      </Typography>
                    );
                  }
                  return null;
                })}
              </Paper>
              <DialogActions>
                <Button onClick={handleRejectTrade} color="secondary">
                  Reject
                </Button>
                <Button
                  onClick={handleAcceptTrade}
                  variant="contained"
                  color="primary"
                  disabled={
                    !currentTrade || !RESOURCES.every(
                      (resource) =>
                        getPlayerResourceCount(currentPlayerColor, resource) >=
                        (currentTrade[RESOURCES.indexOf(resource) + 5] || 0)
                    )
                  }
                >
                  Accept
                </Button>
              </DialogActions>
            </Box>
          ) : isTradeOfferer ? (
            // Trade offerer selects which accepting player to trade with
            <Box className="trade-select-partner">
              <Typography variant="h6">Select Trade Partner</Typography>
              {gameState.colors.map((color, index) => {
                if (color === currentPlayerColor) return null;
                if (gameState.acceptees && gameState.acceptees[index]) {
                  return (
                    <Button
                      key={color}
                      variant="contained"
                      onClick={() => handleConfirmTrade(color)}
                      className="partner-button"
                    >
                      Trade with {color}
                    </Button>
                  );
                }
                return null;
              })}
              <Button onClick={handleCancelTrade} color="secondary" style={{ marginTop: "16px" }}>
                Cancel Trade
              </Button>
            </Box>
          ) : null
        ) : (
          // Normal trade UI
          <Box>
            <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
              <Tab label="Trade with Bank" />
              <Tab label="Trade with Player" />
            </Tabs>

            {tabValue === 0 && (
              <Box className="bank-trade" style={{ marginTop: "16px" }}>
                <Typography variant="subtitle1" style={{ marginBottom: "16px" }}>
                  Trade with the Bank (4:1 ratio, or better with ports)
                </Typography>
                <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
                  <FormControl>
                    <InputLabel>Give</InputLabel>
                    <Select
                      value={bankGiveResource}
                      onChange={(e) => setBankGiveResource(e.target.value as ResourceCard)}
                      label="Give"
                    >
                      {RESOURCES.map((resource) => (
                        <MenuItem key={resource} value={resource}>
                          {resource} (You have: {getPlayerResourceCount(currentPlayerColor, resource)})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    type="number"
                    label="Amount"
                    value={bankGiveAmount}
                    onChange={(e) => setBankGiveAmount(Math.max(1, parseInt(e.target.value) || 4))}
                    inputProps={{ min: 1, max: getPlayerResourceCount(currentPlayerColor, bankGiveResource) }}
                    style={{ width: "100px" }}
                  />
                  <Typography>for</Typography>
                  <FormControl>
                    <InputLabel>Receive</InputLabel>
                    <Select
                      value={bankReceiveResource}
                      onChange={(e) => setBankReceiveResource(e.target.value as ResourceCard)}
                      label="Receive"
                    >
                      {RESOURCES.filter((r) => r !== bankGiveResource).map((resource) => (
                        <MenuItem key={resource} value={resource}>
                          {resource}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
                {!hasEnoughForBankTrade && (
                  <Typography color="error" style={{ marginTop: "8px" }}>
                    You don't have enough {bankGiveResource}
                  </Typography>
                )}
              </Box>
            )}

            {tabValue === 1 && (
              <Box className="player-trade" style={{ marginTop: "16px" }}>
                <FormControl fullWidth style={{ marginBottom: "16px" }}>
                  <InputLabel>Trade with Player</InputLabel>
                  <Select
                    value={selectedPlayer || ""}
                    onChange={(e) => setSelectedPlayer(e.target.value as Color)}
                    label="Trade with Player"
                  >
                    {gameState.colors
                      .filter((color) => color !== currentPlayerColor)
                      .map((color) => (
                        <MenuItem key={color} value={color}>
                          {color}
                        </MenuItem>
                      ))}
                  </Select>
                </FormControl>

                {selectedPlayer && (
                  <>
                    <Box display="flex" gap={2} style={{ marginTop: "16px" }}>
                      <Box flex={1}>
                        <Typography variant="subtitle1" style={{ marginBottom: "8px" }}>
                          You Give:
                        </Typography>
                        {RESOURCES.map((resource) => (
                          <Box key={resource} display="flex" alignItems="center" gap={1} marginBottom={1}>
                            <Typography style={{ minWidth: "80px" }}>{resource}:</Typography>
                            <TextField
                              type="number"
                              size="small"
                              value={playerGiveResources[resource]}
                              onChange={(e) =>
                                setPlayerGiveResources({
                                  ...playerGiveResources,
                                  [resource]: Math.max(0, parseInt(e.target.value) || 0),
                                })
                              }
                              inputProps={{ min: 0, max: getPlayerResourceCount(currentPlayerColor, resource) }}
                              style={{ width: "80px" }}
                            />
                            <Typography variant="caption" style={{ color: "white" }}>
                              (You have: {getPlayerResourceCount(currentPlayerColor, resource)})
                            </Typography>
                          </Box>
                        ))}
                        <Typography variant="caption" style={{ marginTop: "8px", display: "block" }}>
                          Total: {totalGiving}
                        </Typography>
                      </Box>

                      <Box flex={1}>
                        <Typography variant="subtitle1" style={{ marginBottom: "8px" }}>
                          You Receive:
                        </Typography>
                        {RESOURCES.map((resource) => (
                          <Box key={resource} display="flex" alignItems="center" gap={1} marginBottom={1}>
                            <Typography style={{ minWidth: "80px" }}>{resource}:</Typography>
                            <TextField
                              type="number"
                              size="small"
                              value={playerReceiveResources[resource]}
                              onChange={(e) =>
                                setPlayerReceiveResources({
                                  ...playerReceiveResources,
                                  [resource]: Math.max(0, parseInt(e.target.value) || 0),
                                })
                              }
                              inputProps={{ min: 0 }}
                              style={{ width: "80px" }}
                            />
                            <Typography variant="caption" style={{ color: "white" }}>
                              ({selectedPlayer} has: {getPlayerResourceCount(selectedPlayer, resource)})
                            </Typography>
                          </Box>
                        ))}
                        <Typography variant="caption" style={{ marginTop: "8px", display: "block" }}>
                          Total: {totalReceiving}
                        </Typography>
                      </Box>
                    </Box>

                    {(totalGiving === 0 || totalReceiving === 0) && (
                      <Typography color="error" style={{ marginTop: "8px" }}>
                        You must give and receive at least one resource
                      </Typography>
                    )}
                    {!hasEnoughForPlayerTrade && (
                      <Typography color="error" style={{ marginTop: "8px" }}>
                        You don't have enough resources
                      </Typography>
                    )}
                  </>
                )}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      {!hasPendingTrade && (
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          {tabValue === 0 && (
            <Button
              onClick={handleBankTrade}
              variant="contained"
              disabled={!hasEnoughForBankTrade || bankGiveAmount < 1}
            >
              Trade with Bank
            </Button>
          )}
          {tabValue === 1 && (
            <Button
              onClick={handleOfferPlayerTrade}
              variant="contained"
              disabled={
                !selectedPlayer ||
                totalGiving === 0 ||
                totalReceiving === 0 ||
                !hasEnoughForPlayerTrade
              }
            >
              Offer Trade
            </Button>
          )}
        </DialogActions>
      )}
    </Dialog>
  );
}
