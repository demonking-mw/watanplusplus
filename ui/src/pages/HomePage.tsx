import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@mui/material";
import { GridLoader } from "react-spinners";
import { createGame, type BoardConfig } from "../utils/apiClient";
import BoardEditor from "../components/BoardEditor";

import "./HomePage.scss";

// Enum of Type of Game Mode
const GameMode = Object.freeze({
  HUMAN_VS_CATANATRON: "HUMAN_VS_CATANATRON",
  RANDOM_BOTS: "RANDOM_BOTS",
  CATANATRON_BOTS: "CATANATRON_BOTS",
  LOCAL_MULTIPLAYER: "LOCAL_MULTIPLAYER",
});

type GameModeType = typeof GameMode[keyof typeof GameMode]

function getPlayers(gameMode: GameModeType, numPlayers: number) {
  switch (gameMode) {
    case GameMode.HUMAN_VS_CATANATRON:
      const players = ["HUMAN"];
      for (let i = 1; i < numPlayers; i++) {
        players.push("CATANATRON");
      }
      return players;
    case GameMode.RANDOM_BOTS:
      return Array(numPlayers).fill("RANDOM");
    case GameMode.CATANATRON_BOTS:
      return Array(numPlayers).fill("CATANATRON");
    case GameMode.LOCAL_MULTIPLAYER:
      return Array(numPlayers).fill("HUMAN");
    default:
      throw new Error("Invalid Game Mode");
  }
}

type BoardType = "random" | "custom";

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [numPlayers, setNumPlayers] = useState(2);
  const [boardType, setBoardType] = useState<BoardType>("random");
  const [showBoardEditor, setShowBoardEditor] = useState(false);
  const [customBoardConfig, setCustomBoardConfig] = useState<any>(null);
  const navigate = useNavigate();

  const handleCreateGame = async (gameMode: GameModeType) => {
    setLoading(true);
    const players = getPlayers(gameMode, numPlayers);
    const gameId = await createGame(players, boardType === "custom" ? customBoardConfig : undefined);
    setLoading(false);
    navigate("/games/" + gameId);
  };

  const handleBoardTypeChange = (type: BoardType) => {
    setBoardType(type);
    if (type === "custom") {
      setShowBoardEditor(true);
    } else {
      setCustomBoardConfig(null);
    }
  };

  const handleBoardSave = (config: BoardConfig) => {
    setCustomBoardConfig(config);
    setShowBoardEditor(false);
  };

  return (
    <div className="home-page">
      <h1 className="logo">Catanatron</h1>

      <div className="switchable">
        {!loading ? (
          <>
            <div className="player-count-selector">
              <div className="player-count-label">Number of Players</div>
              <div className="player-count-buttons">
                {[2, 3, 4].map((value) => (
                  <Button
                    key={value}
                    variant="contained"
                    onClick={() => setNumPlayers(value)}
                    className={`player-count-button ${
                      numPlayers === value ? "selected" : ""
                    }`}
                  >
                    {value} Players
                  </Button>
                ))}
              </div>
            </div>
            <div className="board-type-selector" style={{ marginTop: "20px", marginBottom: "20px" }}>
              <div className="player-count-label">Board Type</div>
              <div className="player-count-buttons">
                <Button
                  variant={boardType === "random" ? "contained" : "outlined"}
                  onClick={() => handleBoardTypeChange("random")}
                  className={`player-count-button ${
                    boardType === "random" ? "selected" : ""
                  }`}
                >
                  Random
                </Button>
                <Button
                  variant={boardType === "custom" ? "contained" : "outlined"}
                  onClick={() => handleBoardTypeChange("custom")}
                  className={`player-count-button ${
                    boardType === "custom" ? "selected" : ""
                  }`}
                >
                  Custom
                </Button>
              </div>
            </div>
            <Button
              variant="contained"
              color="primary"
              onClick={() => handleCreateGame(GameMode.LOCAL_MULTIPLAYER)}
              disabled={boardType === "custom" && !customBoardConfig}
            >
              Play
            </Button>
            <BoardEditor
              open={showBoardEditor}
              onClose={() => setShowBoardEditor(false)}
              onSave={handleBoardSave}
            />
          </>
        ) : (
          <GridLoader
            className="loader"
            color="#ffffff"
            size={60}
          />
        )}
      </div>
    </div>
  );
}
