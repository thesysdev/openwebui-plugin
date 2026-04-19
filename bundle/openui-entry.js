import React from 'react';
import { createRoot } from 'react-dom/client';
import { Renderer } from '@openuidev/react-lang';
import { openuiChatLibrary } from '@openuidev/react-ui/genui-lib';

window.__OpenUI = { React, createRoot, Renderer, openuiChatLibrary };
